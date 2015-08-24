
from dogu.connection import HTTPConnection


class HTTP2Connection(HTTPConnection):

    def run(self):
        while True:
            pass
            # request, input_stream, end_connection = parse_http2(
            #     self.rfile,
            #     self.stream_dict,
            #     self.encoder,
            #     self.decoder
            # )

            # if end_connection:
            #     break

            # if request is not None:
            #     self.run_with_dogu(request, input_stream)
