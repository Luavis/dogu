"""
    dogu.stream
    ~~~~~~~

"""
from dogu.stream import Stream
from dogu.frame import Frame
from dogu.frame.data_frame import DataFrame
from dogu.frame.header_frame import HeaderFrame
from dogu.data_frame_io import DataFrameIO
from dogu.http2_exception import ProtocolError


class StreamHTTP2(Stream):

    @staticmethod
    def is_server_stream_id(stream_id):
        return stream_id % 2 is 0   # even = server stream

    def __init__(self, conn, stream_id=0):
        Stream.__init__(self, conn, stream_id)
        self.send_headers = list()
        self.request_payload_stream = DataFrameIO()
        self.sending = False

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

        raise ProtocolError('No method in request')

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

    def flush_data(self, results):
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
        data_frame = DataFrame(self.stream_id, end_stream)
        data_frame.data = data

        self.conn.write(data_frame.get_frame_bin())

    def recv_frame(self, frame):
        if isinstance(frame, DataFrame):
            self.recv_data(frame.data)
        elif isinstance(frame, HeaderFrame):
            self.recv_header(frame.get_all())

            if frame.is_end_stream:
                self.end_stream()

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
