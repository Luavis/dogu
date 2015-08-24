"""
    dogu.parse_http
    ~~~~~~~

"""
from dogu.stream import Stream
from dogu.frame import Frame



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
            return (
                target_stream.request_context,
                target_stream.input_stream,
                False,
            )
