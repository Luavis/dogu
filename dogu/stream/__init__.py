"""
    dogu.stream
    ~~~~~~~

"""

try:
    from urllib.parse import quote
except ImportError:
    from urllib import quote


class Stream(object):

    def __init__(self, conn, stream_id=0):
        self.conn = conn
        self.stream_id = stream_id
        self.state = 'idle'

        # recv data
        self.recv_end_header = False
        self.recv_headers = list()
        self.authority = None

        # send data
        self.code = ''
        self.message = ''
        self.push_enabled = False

    def send_response(self, code, message=None):
        self.code = code
        self.message = message

    def send_header(self, name, value):
        pass

    def flush_header(self):
        pass

    def run_stream(self, rfile):
        return False  # end stream default

    def write(self, data):
        pass

    def flush_data(self, data):
        pass

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

        environ['REMOTE_ADDR'] = self.conn.remote_addr

        for (name, value) in headers:
            if not name[0] == ':':  # filter psedo header
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

        environ['REQUEST_METHOD'] = command
        environ['PROTOCOL_VERSION'] = http_version
        environ['SERVER_NAME'] = self.conn.server_setting['host']
        environ['SERVER_PORT'] = str(self.conn.server_setting['port'])
        environ['SCRIPT_NAME'] = ''

        split_path = path.split('?')

        environ['RAW_PATH_INFO'] = split_path[0]
        environ['RAW_QUERY_STRING'] = split_path[1] if len(split_path) > 1 else ''

        environ['PATH_INFO'] = quote(environ['RAW_PATH_INFO'])
        environ['QUERY_STRING'] = quote(environ['RAW_QUERY_STRING'])

        environ['wsgi.input'] = input_stream

        # TODO: error stream connect to error log
        environ['wsgi.errors'] = self.conn.error_stream
        environ['wsgi.version'] = (1, 0)
        environ['wsgi.multithread'] = True
        environ['wsgi.multiprocess'] = False
        environ['wsgi.run_once'] = False
        environ['wsgi.url_scheme'] = 'https' if self.conn.use_ssl else 'http'

        environ['dogu.version'] = (1, 0)

        # TODO : push handler is None temporarily
        environ['dogu.push'] = self.promise
        environ['dogu.push_enabled'] = self.push_enabled

        app = self.conn.get_app_with_host(self.authority if self.authority is not None else environ.get('HTTP_HOST'))

        self.run_app(app, environ)

    def run_app(self, app, environ):
        pass
