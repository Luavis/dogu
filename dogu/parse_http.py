"""
    dogu.server
    ~~~~~~~

"""


def parse_http1(rfile):
    raw_requestline = rfile.readline(65537).decode('us-ascii')

    command = 'GET'
    path = '/'
    http_version = 'HTTP/0.9'

    if len(raw_requestline) > 65536:
        return None  # end request line

    if not raw_requestline:
        return None

    print(raw_requestline)
    requestline = raw_requestline.rstrip('\r\n')

    words = requestline.split()

    if len(words) == 3:
        command, path, http_version = words

        if not http_version[:5] == 'HTTP/':
            return None
        base_version_number = http_version.split('/', 1)[1]
        version_number = base_version_number.split(".")

        # RFC 2145 section 3.1 says there can be only one "." and
        #   - major and minor numbers MUST be treated as
        #      separate integers;
        #   - HTTP/2.4 is a lower version than HTTP/2.13, which in
        #      turn is lower than HTTP/12.3;
        #   - Leading zeros MUST be ignored by recipients.

        if len(version_number) != 2:
            return None

    elif len(words) == 2:
        command, path = words

        if not command == 'GET':
            return None
    else:
        return None

    header_size = len(requestline)
    headers = list()

    while header_size < 65536:
        header_line = rfile.readline(65537).decode('us-ascii').rstrip('\r\n')

        if len(header_line) == 0:
            break

        header_size += len(header_line)

        if not header_line.lstrip() == header_line:
            if not len(headers) == 0:
                return None

            headers[-1][1] = header_line.lstrip()

            continue

        headers.append(tuple(header_words.lstrip() for header_words in header_line.split(':')))

    return (command, path, http_version, headers)


def parse_stream(rfile):
    return None
