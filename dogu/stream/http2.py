"""
    dogu.stream
    ~~~~~~~

"""
from dogu.stream import Stream
from dogu.frame.data_frame import DataFrame
from dogu.frame.header_frame import HeaderFrame
from dogu.data_frame_io import DataFrameIO
from dogu.http2_exception import ProtocolError


class StreamHTTP2(Stream):

    def __init__(self, conn, scheme='https', stream_id=0):
        Stream.__init__(self, conn, scheme, stream_id)
        self.input_stream = DataFrameIO()

    @property
    def is_wait_res(self):
        return self.state == 'half-closed(remote)'

    def send_header(self, name, value):
        pass

    def flush_header(self):
        pass

    def run_stream(self, rfile):
        pass

    def write(self, data):
        pass

    def recv_frame(self, frame):
        if isinstance(frame, DataFrame):
            self.recv_data(frame.data)
        elif isinstance(frame, HeaderFrame):
            self.recv_header(frame.get_all())

            if frame.is_end_stream:
                self._command = frame.method
                self._path = frame.path
                self._authority = frame.authority
                self._scheme = frame.scheme

                self.end_stream()

    def recv_header(self, headers):
        if self.recv_end_header is True:
            raise ProtocolError('header is already end')

        if self.state is 'idle':
            print('open!!')
            self.state = 'open'  # stream opened
        elif self.state is not 'open':
            raise ProtocolError('stream is not opened')

        self.recv_headers.extend(headers)

    def recv_data(self, data):
        self.input_buffer.write(data)

    def end_header(self):
        self.recv_end_header = True

    def end_stream(self):
        if self.state is 'open':
            self.state = 'half-closed(remote)'
