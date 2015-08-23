"""
    dogu.connection
    ~~~~~~~

"""

import sys

from dogu.parse_http import parse_http2, parse_http1
from dogu.hpack.hpack import Encoder, Decoder
try:
    from urllib.parse import quote
except ImportError:
    from urllib import quote


class HTTPConnection(object):

    def __init__(self, is_http2, remote_addr, server_setting, app_list, rfile, wfile):
        self.is_http2 = is_http2
        self.server_setting = server_setting
        self.rfile = rfile
        self.wfile = wfile
        self.remote_addr = remote_addr

        self.stream_dict = dict()
        self.app_list = app_list
        self.encoder = Encoder()
        self.decoder = Decoder()
        self.use_ssl = self.server_setting['use_ssl']

    def run(self):
        while True:
            if self.is_http2:
                request, end_connection = parse_http2(
                    self.rfile,
                    self.stream_dict,
                    self.encoder,
                    self.decoder
                )
            else:
                request, end_connection = parse_http1(self.rfile)
                input_stream = self.rfile

            if end_connection:
                break

            if request is not None:
                self.run_with_dogu(request, input_stream)

    def get_app_with_host(self, host):
        try:
            domain = host.split(':')[0]
            app = self.app_list.get(domain)
        except:
            app = None

        if app is None:  # can not find app by domain
            app = self.app_list.get('default')  # find default

            if app is None:
                raise ValueError('unknown domain')  # TODO catch error

        return app

    def send_response(self, code, message=None):
        # if message is None:
            # message = code in self.responses and self.responses[code][0] or ''
        # if self.request_version != 'HTTP/0.9' and self.request_version != 'HTTP/2.0':
        hdr = "%s %s %s\r\n" % ('HTTP/1.1', code, message)  # TODO : fix it later
        self.wfile.write(hdr.encode('ascii'))
        # elif self.request_version == 'HTTP/2.0':
        # self.send_header(':status', str(code))
        # self.send_header(':scheme', 'https')

    def send_header(self, name, value):
        self.wfile.write((name + ': ' + value + '\r\n').encode('iso-8859-1'))

    def flush_header(self):
        self.wfile.write(b'\r\n')  # end header
        self.wfile.flush()

    def write(self, data):
        self.wfile.write(data)

    def start_response(self, status, response_headers, exc_info=None):
        try:
            code, msg = status.split(None, 1)
        except ValueError:
            code, msg = status, None

        self.send_response(code, msg)

        for name, value in response_headers:
            self.send_header(name, value)

        self.flush_header()

        return self.write

    def run_with_dogu(self, request, input_stream):

        (command, path, http_version, headers) = request
        environ = dict()

        environ['REMOTE_ADDR'] = self.remote_addr

        for (name, value) in headers:
            environ['HTTP_' + name.upper().replace('-', '_')] = value

        if environ.get('HTTP_CONTENT_LENGTH'):
            environ['CONTENT_LENGTH'] = environ['HTTP_CONTENT_LENGTH']
            del environ['HTTP_CONTENT_LENGTH']
        else:
            environ['CONTENT_LENGTH'] = '0'

        if environ.get('HTTP_CONTENT_TYPE'):
            environ['CONTENT_TYPE'] = environ['HTTP_CONTENT_TYPE']
            del environ['HTTP_CONTENT_TYPE']
        else:
            environ['CONTENT_TYPE'] = ''

        environ['HTTP_METHOD'] = command
        environ['PROTOCOL_VERSION'] = http_version
        environ['SERVER_NAME'] = self.server_setting['host']
        environ['SERVER_PORT'] = self.server_setting['port']
        environ['SCRIPT_NAME'] = ''

        split_path = path.split('?')

        environ['RAW_QUERY_STRING'] = split_path[0]
        environ['RAW_PATH_INFO'] = split_path[1] if len(split_path) > 1 else ''

        environ['QUERY_STRING'] = quote(environ['RAW_QUERY_STRING'])
        environ['PATH_INFO'] = quote(environ['RAW_PATH_INFO'])

        environ['wsgi.input'] = input_stream

        # TODO: error stream connect to error log
        environ['wsgi.errors'] = sys.stderr
        environ['wsgi.version'] = (1, 0)
        environ['wsgi.multithread'] = True
        environ['wsgi.multiprocess'] = False
        environ['wsgi.run_once'] = False
        environ['wsgi.url_scheme'] = 'https' if self.use_ssl else 'http'

        environ['dogu.version'] = (1, 0)

        # TODO : push handler is None temporarily
        environ['dogu.push'] = None
        environ['dogu.push_enabled'] = True

        app = self.get_app_with_host(environ.get('HTTP_HOST'))

        app(environ, self.start_response)

        self.wfile.flush()
