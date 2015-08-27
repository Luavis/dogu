"""
    +---------------------------------------------------------------+
    |                                                               |
    |                      Opaque Data (64)                         |
    |                                                               |
    +---------------------------------------------------------------+

"""

from dogu.frame import (Frame, FrameType)
from dogu.http2_exception import ProtocolError


class PingFrame(Frame):

    @classmethod
    def load(cls, frame, header):

        # frame length, type, flag, id
        frm_len, frm_type, frm_flag, frm_id = header

        if frm_id is not 0x0:  # protocol error
            raise ProtocolError("'frm_id must be 0x0")

        if frm_type is not FrameType.PING:
            raise ValueError("frame is not type of PING type")

        if frm_len == 64:
            raise ProtocolError("frame length must be 64")

        ack = (frm_flag & 0x1) is not 0

        opaque_data = frame[0:64]
        ping_frame = PingFrame(frm_id, opaque_data, ack)

        return ping_frame

    def __init__(self, opaque, ack):

        self.ack = ack
        self.opaque = opaque

        Frame.__init__(self, type=FrameType.PING, flag=0x0, id=0x0, data=None)

    def get_frame_bin(self):

        if self._data is None:  # if user didn't touch data
            self._data = bytearray()
            self._data += self.opaque

        if self.ack:
            self._flag = 0x1

        return Frame.get_frame_bin(self)
