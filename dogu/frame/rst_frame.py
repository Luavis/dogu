"""
    +---------------------------------------------------------------+
    |                        Error Code (32)                        |
    +---------------------------------------------------------------+

"""

from dogu.frame import (Frame, FrameType)
from dogu.util import int_to_bytes
from dogu.http2_exception import ProtocolError


class RSTFrame(Frame):

    @classmethod
    def load(cls, frame, header, **kargs):

        # frame length, type, flag, id
        frm_len, frm_type, frm_flag, frm_id = header

        if frm_id is 0x0:  # protocol error
            raise ProtocolError("'frm_id must not be 0x0")

        if frm_type is not FrameType.RST_STREAM:
            raise ValueError("frame is not type of RST_STREAM type")
        if not frm_len == 4:
            raise ProtocolError('RST_STREAM lenght must be 4')

        error_code = frame[0] << 24
        error_code += frame[1] << 16
        error_code += frame[2] << 8
        error_code += frame[3]

        rst_frame = RSTFrame(frm_id, error_code)

        return rst_frame

    def __init__(self, id, error_code):

        self.error_code = error_code

        Frame.__init__(self, type=FrameType.PRIORITY, flag=0x0, id=id, data=None)

    def get_frame_bin(self):

        if self._data is None:  # if user didn't touch data
            self._data = int_to_bytes(self.error_code, 4)

        return Frame.get_frame_bin(self)
