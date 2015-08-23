"""
    dogu.stream
    ~~~~~~~

"""

from dogu.http2_exception import ProtocolError
from dogu.frame.header_frame import HeaderFrame
from dogu.frame.data_frame import DataFrame

class Stream(object):

    def __init__(self, stream_id):
        self.stream_id = stream_id
        self.state = 'idle'
        self.recv_end_header = False

        self.recv_headers = []

    @property
    def is_wait_res(self):
        return self.state == 'half-closed(remote)'

    @property
    def request_context(self):
        return None

# TODO: if property can not found it occur ProtocolError

    @property
    def command(self):
        return self._command

    @property
    def path(self):
        return self._path

    @property
    def authority(self):
        return self._authority

    @property
    def scheme(self):
        return self._scheme

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
        pass

    def end_header(self):
        self.recv_end_header = True

    def end_stream(self):
        if self.state is 'open':
            self.state = 'half-closed(remote)'
