"""
    dogu.parse_http
    ~~~~~~~

"""
from dogu.stream import Stream
from dogu.frame import Frame


def parse_http1(rfile):
    raw_requestline = rfile.readline(65537).decode('us-ascii')

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
        header_line = rfile.readline(65537).decode('us-ascii').rstrip('\r\n')

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

    return (command, path, http_version, headers), False


def parse_http2(rfile, stream_dict, encoder, decoder):
    while True:
        raw_frame_header = rfile.read(9)

        frame_header = Frame.parse_header(raw_frame_header[:9])
        (frame_len, frame_type, frame_flag, frame_id) = frame_header
        frame_len = frame_header[0]

        raw_frame_payload = rfile.read(frame_len)
        frame = Frame.load(raw_frame_header + raw_frame_payload)

        if stream_dict.get(frame_id) is None:
            target_stream = stream_dict[frame_id] = Stream(frame_id)
        else:
            target_stream = stream_dict[frame_id]

        target_stream.recv_frame(frame)

        if target_stream.is_wait_res:
            print('ready send')
            return (
                target_stream.command,
                target_stream.path,
                'HTTP/2.0',
                target_stream.recv_headers
            ), False