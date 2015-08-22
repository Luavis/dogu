"""
    dogu.stream
    ~~~~~~~

"""

from dogu.http2_errors import ProtocolError


class Stream(object):

    def __init__(self, stream_id):
        self.stream_id = stream_id
        self.state = 'idle'
        self.recv_end_header = False
        self.recv_headers = []

    @property
    def is_wait_res(self):
        return self.state is 'half-closed(remote)'

    @property
    def request_context(self):
        return None

    def recv_header(self, headers):
        if self.recv_end_header is True:
            raise ProtocolError('header is already end')

        if self.state is 'idle':
            self.state = 'open'  # stream opened
        elif self.state is not 'open':
            raise ProtocolError('stream is not opened')

        self.recv_headers.extend(headers)

    def recv_data(self):
        pass

    def end_header(self):
        self.recv_end_header = True

    def end_stream(self):
        if self.state == 'open':
            self.state = 'half-closed(remote)'
