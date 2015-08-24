
from dogu.connection import HTTPConnection
from dogu.stream.http1 import StreamHTTP1

class HTTP1Connection(HTTPConnection):

    def run(self):
        while True:
            stream_http1 = StreamHTTP1(self)
            if not stream_http1.run_stream(self.rfile):  # close connection
                break
