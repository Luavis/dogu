"""
    dogu.connection
    ~~~~~~~

"""

from dogu.parse_http import parse_http2, parse_http1
from dogu.hpack.hpack import Encoder, Decoder


class HTTPConnection(object):

    def __init__(self, remote_addr, is_http2, server_setting, rfile, wfile):
        self.is_http2 = is_http2
        self.server_setting = server_setting
        self.rfile = rfile
        self.wfile = wfile
        self.remote_addr = remote_addr

        self.stream_dict = dict()
        self.encoder = Encoder()
        self.decoder = Decoder()

    def run(self):
        while True:
            if self.is_http2:

                request, end_connection = parse_http2(self.rfile, self.stream_dict, self.encoder, self.decoder)
            else:
                request, end_connection = parse_http1(self.rfile)

            if end_connection:
                break

            if request is not None:
                cgi_headers.append()

        def run_with_dogu(self, request, input):

            (command, path, http_version, headers) = request
            environ = dict()

            environ['REMOTE_ADDR'] = self.remote_addr
            environ['CONTENT_TYPE']

            for name, value in headers:
                environ['HTTP_' + name.upper().replace('-', '_')] = value

            if environ.get('HTTP_CONTENT_LENGTH'):
                environ['CONTENT_LENGTH'] = environ['HTTP_CONTENT_LENGTH']
                del environ['HTTP_CONTENT_LENGTH']
            else:
                environ['CONTENT_LENGTH'] = '0'


