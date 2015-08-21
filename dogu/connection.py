"""
    dogu.connection
    ~~~~~~~

"""

from dogu.parse_http import parse_http2, parse_http1


class HTTPConnection(object):

    def __init__(self, is_http2, server_setting, rfile, wfile):
        self.is_http2 = is_http2
        self.server_setting = server_setting
        self.rfile = rfile
        self.wfile = wfile

        self.stream_dict = dict()

    def run(self):
        while True:
            if self.is_http2:
                request, end_connection = parse_http2(self.rfile, self.stream_dict)
            else:
                request, end_connection = parse_http1(self.rfile)

            if end_connection:
                break
