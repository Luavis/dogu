"""
    dogu.parse_http
    ~~~~~~~

"""
from struct import unpack
from dogu.stream import Stream


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

        headers.append(tuple(header_words.lstrip() for header_words in header_line.split(':', 1)))

    return (command, path, http_version, headers), False


def parse_http2(rfile, stream_dict, encoder, decoder):
    while True:
        raw_frame_header = rfile.read(9)

        length_1, length_left, type_id, flag, stream_id = unpack('!BHBBL', raw_frame_header)
        length = length_1 * 16 * 16 + length_left

        frame_type = 'DATA'

        try:
            frame_type = [
                'DATA',
                'HEADERS',
                'PRIORITY',
                'RST_STREAM',
                'SETTINGS',
                'PUSH_PROMISE',
                'PING',
                'GOAWAY',
                'WINDOW_UPDATE',
                'CONTINUATION'
            ].index(type_id)
        except ValueError:
            continue  # ignore unknown frame

        if stream_dict.get(stream_id) is None:
            stream_dict[stream_id] = Stream(stream_id, )

        target_stream = stream_dict[stream_id]

        # set frame header
        frame_header = (length, type_id, flag, stream_id)

        # read left frame payload
        payload = rfile.read(length)

        if type_id == 0:
            (options, data) = parse_data_frame(frame_header, payload)
            target_stream.recv_data(encoder.encode(data))
        elif type_id == 1:
            (options, data) = parse_header_frame(frame_header, payload)
            target_stream.recv_header(encoder.encode(data))

        if options.get('end_headers') is True:
            target_stream.end_stream()

        if options.get('end_stream') is True:
            target_stream.end_stream()

        if target_stream.is_wait_res:
            return target_stream.request_context, False
        else:
            return None, False


def parse_data_frame(frame_header, payload):
    length, type_id, flag, stream_id = frame_header
    flags = dict()

    if type_id & 1:
        flags['end_stream'] = True
    else:
        flags['end_stream'] = False

    if type_id & 8:
        pad_length = ord(payload[0])
        (data, ) = unpack('x' + str(length - pad_length - 1) + 'p' + str(pad_length) + 'x', payload)

        return (flags, data)
    else:
        return (flags, payload)

def parse_header_frame(frame_header, payload):
    length, type_id, flag, stream_id = frame_header
    flags = dict()

    is_pad = (type_id & 8) is not 0
    is_priority = (type_id & 0x20) is not 0
    if is_pad:
        pad_length = ord(payload[0])
    else:
        pad_length = 0

    if type_id & 1:
        flags['end_stream'] = True
    else:
        flags['end_stream'] = False

    if type_id & 4:
        flags['end_headers'] = True
    else:
        flags['end_headers'] = False

    if is_priority:
        frm = str(int(is_pad)) + 'x'
        + 'IB'
        + str(length - pad_length - 1) + 'p'
        + str(pad_length) + 'x'

        (dep_id, weight, header_frag, ) = unpack(frm, payload)

        flags['is_exclusive'] = dep_id & 0x80000000 is not 0
        flags['dep_id'] = dep_id & 0x7FFFFFFF
    else:
        frm = str(int(is_pad)) + 'x'
        + str(length - pad_length - 1) + 'p'
        + str(pad_length) + 'x'

        (header_frag, ) = unpack(frm, payload)

    return (flags, header_frag)