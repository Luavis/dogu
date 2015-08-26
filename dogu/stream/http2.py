"""
    dogu.stream
    ~~~~~~~

"""
from dogu.stream import Stream
from dogu.frame import Frame
from dogu.frame.data_frame import DataFrame
from dogu.frame.header_frame import HeaderFrame
from dogu.frame.rst_frame import RSTFrame
from dogu.frame.ping_frame import PingFrame
from dogu.frame.push_promise_frame import PushPromiseFrame
from dogu.data_frame_io import DataFrameIO
from dogu.http2_exception import ProtocolError
from dogu.http2_error_codes import error_codes
from gevent import spawn, sleep
from dogu.logger import logger

class StreamHTTP2(Stream):

    INITIAL_WINDOW_SIZE = 65535

    @staticmethod
    def is_server_stream_id(stream_id):
        return stream_id % 2 is 0   # even = server stream

    def __init__(self, conn, stream_id=0):
        Stream.__init__(self, conn, stream_id)
        self.send_headers = list()
        self.request_payload_stream = DataFrameIO()
        self.sending = False
        self.window_size = StreamHTTP2.INITIAL_WINDOW_SIZE
        self.send_size = 0
        self.push_enabled = True  # default push is enabled

    def send_response(self, code, message=None):
        Stream.send_response(self, code, message)

        self.send_header(':status', str(code))
        self.send_header(':scheme', self.scheme)

    @property
    def is_wait_res(self):
        return self.state == 'half-closed(remote)' and \
            not self.sending

    @property
    def is_closed(self):
        return self.state == 'closed'

    @property
    def command(self):
        for header in self.recv_headers:
            if header[0] == ':method':
                return header[1]

        raise ProtocolError('No method in request')

    @property
    def scheme(self):
        for header in self.recv_headers:
            if header[0] == ':scheme':
                return header[1]

        raise ProtocolError('No scheme in request')

    @property
    def path(self):
        for header in self.recv_headers:
            if header[0] == ':path':
                return header[1]

        raise ProtocolError('No path in request')

    @property
    def http_version(self):
        return 'HTTP/2.0'

    def send_header(self, name, value):
        self.send_headers.append((name.lower(), str(value)))

    def flush_header(self):
        h_frame = HeaderFrame(self.stream_id, self.send_headers)

        self.conn.write(h_frame.get_frame_bin())
        self.conn.flush()

    def run_app_in_spawn(self, app, environ):
        try:
            data = app(environ, self.start_response)
            self.flush_data(data)
        except OSError:
            logger.debug('user close connection')

    def run_app(self, app, environ):
        spawn(self.run_app_in_spawn, app, environ)

    def flush_data(self, results):
        logger.debug('flush data in %d' % self.stream_id)

        if results is not None:
            for result in results:
                self.write(result)

        self.write(b'', end_stream=True)

        self.conn.flush()
        self.state = 'closed'

    def run_stream(self, rfile, frame_header):
        (frame_len, frame_type, frame_flag, frame_id) = frame_header
        raw_frame_payload = rfile.read(frame_len)

        frame = Frame.load(
            frame=raw_frame_payload,
            header=frame_header,
            decoder=self.conn.decoder
        )

        self.recv_frame(frame)

        if self.is_wait_res:

            self.sending = True  # start send

            self.run_with_dogu(
                (
                    self.command,
                    self.path,
                    self.http_version,
                    self.recv_headers,
                ),
                self.request_payload_stream
            )

        return True

    def write(self, data, end_stream=False):
        data_len = len(data)
        logger.debug('write in stream %d data length: %d end_stream %d' % (self.stream_id, data_len, end_stream))
        left_len = self.window_size - self.send_size

        if data_len > left_len:

            # send data
            data_frame = DataFrame(self.stream_id)
            data_frame.data = data[:left_len]

            self.conn.write(data_frame.get_frame_bin())
            self.conn.flush()

            # re-initialize
            self.send_size = data_len + left_len
            data = data[left_len:]

            while self.send_size + data_len > self.window_size:
                logger.debug('wait for flow control')
                sleep(0)  # wait for get flow control

        data_frame = DataFrame(self.stream_id, end_stream)
        data_frame.data = data

        self.conn.write(data_frame.get_frame_bin())
        self.send_size += data_len

    def recv_frame(self, frame):
        if isinstance(frame, DataFrame):
            self.recv_data(frame.data)

            if frame.is_end_stream:
                self.end_stream()
        elif isinstance(frame, HeaderFrame):
            self.recv_header(frame.get_all())

            if frame.is_end_stream:
                self.end_stream()
        elif isinstance(frame, PingFrame):
            if not frame.ack:
                ping = PingFrame(frame.opaque, True)
                self.conn.write(ping.get_frame_bin())
        elif isinstance(frame, RSTFrame):
            self.state = 'closed'
            logger.error('user reset stream %s' % error_codes[frame.error_code])

    def promise(self, push_headers):

        push_promise = PushPromiseFrame(self.stream_id, push_headers)
        push_stream = self.conn.create_stream()

        push_promise.promised_stream_id = push_stream.stream_id
        promise = push_promise.get_frame_bin()
        logger.debug('send promise stream\n%s' % push_promise)

        self.conn.write(promise)  # promise push
        self.conn.flush()

        spawn(push_stream.push, push_headers)

    def push(self, push_headers):
        self.state = 'reserved(local)'

        self.recv_headers.extend(push_headers)

        self.run_with_dogu(  # run application
            (
                self.command,
                self.path,
                self.http_version,
                self.recv_headers,
            ),
            self.request_payload_stream  # empty stream
        )

    def recv_header(self, headers):
        if self.recv_end_header is True:
            raise ProtocolError('header is already end')

        if self.state is 'idle':
            self.state = 'open'  # stream opened
        elif self.state is not 'open':
            raise ProtocolError('stream is not opened')

        self.recv_headers.extend(headers)

    def recv_data(self, data):
        self.request_payload_stream.write(data)

    def end_header(self):
        self.recv_end_header = True

    def end_stream(self):
        if self.state is 'open':
            self.state = 'half-closed(remote)'
