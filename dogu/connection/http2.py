"""
    dogu.http2.connection
    ~~~~~~~

"""
from dogu.connection import HTTPConnection
from hpack.hpack import Encoder, Decoder
from dogu.stream.http2 import StreamHTTP2
from dogu.http2_exception import StreamClosedError
from dogu.frame import Frame, FrameType

class HTTP2Connection(HTTPConnection):

    STREAM_HEADER_SIZE = 9

    def __init__(
        self,
        is_http2,
        remote_addr,
        server_setting,
        app_list,
        rfile,
        wfile
    ):
        HTTPConnection.__init__(
            self,
            is_http2,
            remote_addr,
            server_setting,
            app_list,
            rfile,
            wfile)

        self.encoder = Encoder()
        self.decoder = Decoder()
        self.last_stream_id = 0

        self.stream_dict[0] = StreamHTTP2(
            self,
            stream_id=0
        )

    def create_stream(self):  # when server create stream

        self.last_stream_id += 2  # update last stream id
        stream = StreamHTTP2(self, self.last_stream_id)
        self.register_stream(self.last_stream_id, stream)

        return stream

    def created_stream(self, stream_id):  # when client create stream

        stream = StreamHTTP2(self, stream_id)
        self.register_stream(stream_id, stream)

        return stream

    def register_stream(self, stream_id, stream):
        self.stream_dict[stream_id] = stream

    def get_stream(self, stream_id):
        stream = self.stream_dict.get(stream_id)

        if stream is not None:
            if stream.is_closed:
                raise StreamClosedError()  # if closed stream raise exception
        else:
            if StreamHTTP2.is_server_stream_id(stream_id):
                stream = self.create_stream()
            else:
                stream = self.created_stream(stream_id)

        return stream

    def run(self):
        while True:
            raw_frame_header = self.rfile.read(
                HTTP2Connection.STREAM_HEADER_SIZE
            )

            if len(raw_frame_header) == 0:  # user close connection
                return

            frame_header = Frame.parse_header(
                raw_frame_header[:HTTP2Connection.STREAM_HEADER_SIZE]
            )

            (frame_len, frame_type, frame_flag, frame_id) = frame_header

            try:
                target_stream = self.get_stream(frame_id)
            except StreamClosedError:  # if closed error

                if not (frame_type == FrameType.WINDOW_UPDATE or
                        frame_type == FrameType.PRIORITY):
                    raise StreamClosedError()

            # close connection
            if not target_stream.run_stream(self.rfile, frame_header):
                break
