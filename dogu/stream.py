"""
    dogu.stream
    ~~~~~~~

"""
from dogu.frame import Frame

class Stream(object):

    def __init__(self, stream_id, hpack):
        self.stream_id = stream_id
        self.state = 'idle'
        (self.encoder, self.decoder) = hpack

    @property
    def is_wait_res(self):
        return self.state is 'half-closed(remote)'

    @property
    def request_context(self):
        return None

    def recv_frame(self, frame_header, raw_frame):
        frame = Frame.load(frame_header, raw_frame)

        if frame is None:  # unsupport frame
            return None

        
