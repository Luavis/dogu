"""
    +-+-------------------------------------------------------------+
    |R|              Window Size Increment (31)                     |
    +-+-------------------------------------------------------------+

"""

from dogu.frame import (Frame, FrameType)
from dogu.util import int_to_bytes
from dogu.http2_exception import FrameSizeError, ProtocolError

class WindowUpdateFrame(Frame):

    WINDOW_UPDATE_MAX_SIZE = 2147483647  # 2^31 - 1

    @classmethod
    def load(cls, frame, header, **kargs):

        # frame length, type, flag, id
        frm_len, frm_type, frm_flag, frm_id = header

        if frm_len is not 4:
            raise FrameSizeError

        window_size = frame[0] << 24
        window_size += frame[1] << 16
        window_size += frame[2] << 8
        window_size += frame[3]

        if (window_size < 1 or
                window_size > WindowUpdateFrame.WINDOW_UPDATE_MAX_SIZE):
            raise ProtocolError()

        window_frame = WindowUpdateFrame(frm_id, window_size)

        return window_frame

    def __init__(self, id, window_size=1):
        Frame.__init__(
            self,
            type=FrameType.WINDOW_UPDATE,
            flag=0x0,
            id=id,
            data=None
        )
        self.window_size = window_size

    def get_frame_bin(self):

        if self._data is None:
            self._data = int_to_bytes(self.window_size, 4)

        return Frame.get_frame_bin(self)
