"""
    dogu.http2
    ~~~~~~~

"""

from dogu.frame import Frame
from dogu.frame.data_frame import DataFrame
from dogu.frame.header_frame import HeaderFrame
from dogu.frame.rst_frame import RSTFrame
from dogu.frame.setting_frame import SettingFrame
from dogu.frame.ping_frame import PingFrame
from dogu.frame.window_update import WindowUpdateFrame
from dogu.frame.push_promise_frame import PushPromiseFrame

from dogu.stream import Stream
from dogu.data_frame_io import DataFrameIO
from dogu.http2_exception import ProtocolError
from dogu.http2_error_codes import error_codes
from gevent import spawn, sleep
from dogu.logger import logger


class StreamHTTP2(Stream):

    UPDATE_WINDOW_SIZE = 3145737
    CONNECTION_STREAM_ID = 0x0

    @staticmethod
    def is_server_stream_id(stream_id):
        return stream_id % 2 is 0   # even = server stream

    def __init__(self, conn, stream_id=0):
        Stream.__init__(self, conn, stream_id)
        self.send_headers = list()
        self.request_payload_stream = DataFrameIO()
        self.sending = False
        self.is_run_app = False
        self.is_recv_end_header = False
        self.send_window_size = self.conn.send_initial_window_size
        self.recv_window_size = self.conn.recv_initial_window_size
        self.send_size = 0
        self.recv_size = 0
        self.push_enabled = True  # default push is enabled

    def send_response(self, code, message=None):
        Stream.send_response(self, code, message)

        self.send_header(':status', str(code))
        self.send_header(':scheme', self.scheme)

    @property
    def is_wait_res(self):
        return self.state == 'half-closed(remote)'

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

        if self.is_wait_res:
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

        if self.is_wait_res:
            self.conn.flush()
            self.state = 'half-closed(remote)'

    def run_stream(self, rfile, frame_header):
        (frame_len, frame_type, frame_flag, frame_id) = frame_header
        raw_frame_payload = rfile.read(frame_len)

        frame = Frame.load(
            frame=raw_frame_payload,
            header=frame_header,
            decoder=self.conn.decoder
        )

        self.recv_frame(frame)

        if self.is_recv_end_header and not self.is_run_app:
            self.is_run_app = True

            self.run_with_dogu(
                (
                    self.command,
                    self.path,
                    self.http_version,
                    self.recv_headers,
                ),
                self.request_payload_stream
            )

        if self.is_wait_res and not self.sending:
            self.sending = True  # start send
            self.conn.flush()

        return True

    def write(self, data, end_stream=False):
        data_len = len(data)
        # logger.debug('write in stream %d data length: %d end_stream %d' % (self.stream_id, data_len, end_stream))

        left_len = self.send_window_size - self.send_size
        # logger.debug('send window size: %d left length: %d', self.send_window_size, left_len)

        if data_len > left_len:

            # send data
            data_frame = DataFrame(self.stream_id)
            data_frame.data = data[:left_len]

            self.conn.write(data_frame.get_frame_bin())
            self.conn.flush()

            # re-initialize
            self.send_size += left_len
            data = data[left_len:]
            data_len = len(data)
            logger.debug('wait for flow control')

            while self.send_size + data_len > self.send_window_size:
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
            if frame.is_end_header:
                self.is_recv_end_header = True
            if frame.is_end_stream:
                self.end_stream()
        elif isinstance(frame, PingFrame):
            if not frame.ack:
                ping = PingFrame(frame.opaque, True)
                self.conn.write(ping.get_frame_bin())
        elif isinstance(frame, WindowUpdateFrame):
            logger.debug('window update %d in stream %d', frame.window_size, self.stream_id)

            if self.stream_id == StreamHTTP2.CONNECTION_STREAM_ID:
                self.conn.send_initial_window_size += frame.window_size
            self.send_window_size += frame.window_size
        elif isinstance(frame, SettingFrame):
            for setting in frame.setting_list:
                if setting[0] == SettingFrame.SETTINGS_MAX_FRAME_SIZE:
                    self.conn.send_initial_window_size = setting[1]
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
        data_len = len(data)
        left_len = self.recv_window_size - self.recv_size

        if data_len > left_len:
            raise ProtocolError()

        self.recv_size += len(data)
        self.request_payload_stream.write(data)

        left_len = self.recv_window_size - self.recv_size

        if left_len < StreamHTTP2.UPDATE_WINDOW_SIZE:  # new left size is wait for recv more
            window_update = WindowUpdateFrame(
                self.stream_id,
                StreamHTTP2.UPDATE_WINDOW_SIZE
            )

            self.conn.write(window_update.get_frame_bin())
            self.conn.flush()

            window_update = WindowUpdateFrame(
                0x0,
                StreamHTTP2.UPDATE_WINDOW_SIZE * 2
            )

            self.conn.write(window_update.get_frame_bin())
            self.conn.flush()

            self.recv_window_size += StreamHTTP2.UPDATE_WINDOW_SIZE
            logger.debug('update window size %d', self.recv_window_size)

    def end_header(self):
        self.recv_end_header = True

    def end_stream(self):
        if self.state is 'open':
            self.state = 'half-closed(remote)'
        elif self.state == 'half-closed(remote)':
            self.conn.flush()
            self.state = 'closed'
