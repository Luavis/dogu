"""
    dogu.http1.connection
    ~~~~~~~

"""
from dogu.stream import Stream
from gevent import monkey

monkey.patch_all()

class StreamHTTP1(Stream):

    DEFAULT_ENCODING_TYPE = 'iso-8859-1'
    EOL_MARKER = '\r\n'.encode('iso-8859-1')

    def __init__(self, conn, stream_id=0):
        Stream.__init__(self, conn, stream_id)
        self.promise = None  # no push handler

    def send_response(self, code, message=None):
        self.code = code
        self.message = message

        self.conn.wfile.write(
            (self.http_version + ' ' + code + ' ' + message).encode(
                StreamHTTP1.DEFAULT_ENCODING_TYPE
            )
        )

        self.conn.wfile.write(StreamHTTP1.EOL_MARKER)

    def send_header(self, name, value):
        self.conn.wfile.write(
            ('%s: %s\r\n' % (name, value))
            .encode(StreamHTTP1.DEFAULT_ENCODING_TYPE)
        )

    def flush_header(self):
        self.conn.write(StreamHTTP1.EOL_MARKER)
        self.conn.wfile.flush()

    def write(self, data):
        self.conn.write(data)

    def flush_data(self, results):
        if results is not None:
            for result in results:
                self.conn.write(result)

        self.conn.flush()

    def run_stream(self, rfile):
        request, end_connection = self.parse_request(rfile)

        if request is not None:
            command, path, http_version, headers = request
            self.http_version = http_version  # get HTTP version in requset
            self.run_with_dogu(request, rfile)
        else:  # this case probably malformed request
            return False

        if end_connection:
            return False
        else:
            return True

    def run_app(self, app, environ):
        data = app(environ, self.start_response)

        self.flush_data(data)

    def parse_request(self, rfile):
        raw_requestline = rfile.readline(65537).decode(
            StreamHTTP1.DEFAULT_ENCODING_TYPE
        )

        if len(raw_requestline) == 0:
            return None, True  # user end connection

        command = 'GET'
        path = '/'
        http_version = 'HTTP/0.9'

        if len(raw_requestline) > 65536:
            return None, True  # end request line

        if not raw_requestline:
            return None, True

        requestline = raw_requestline.rstrip('\r\n')

        words = requestline.split()

        if len(words) == 3:
            command, path, http_version = words

            if not http_version[:5] == 'HTTP/':
                return None, True
            base_version_number = http_version.split('/', 1)[1]
            version_number = base_version_number.split(".")

            # RFC 2145 section 3.1 says there can be only one "." and
            #   - major and minor numbers MUST be treated as
            #      separate integers;
            #   - HTTP/2.4 is a lower version than HTTP/2.13, which in
            #      turn is lower than HTTP/12.3;
            #   - Leading zeros MUST be ignored by recipients.

            if len(version_number) != 2:
                return None, True

        elif len(words) == 2:
            command, path = words

            if not command == 'GET':
                return None, True
        else:
            return None, True

        header_size = len(requestline)
        headers = list()

        while header_size < 65536:
            header_line = rfile.readline(65537).decode(StreamHTTP1.DEFAULT_ENCODING_TYPE).rstrip('\r\n')

            if len(header_line) == 0:
                break

            header_size += len(header_line)

            if not header_line.lstrip() == header_line:
                if not len(headers) == 0:
                    return None, True

                headers[-1][1] = header_line.lstrip()

                continue

            headers.append(
                tuple(header_words.lstrip() for header_words in header_line.split(':', 1))
            )

        return (command, path, http_version, headers, ), False
