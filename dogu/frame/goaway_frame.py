"""
    +-+-------------------------------------------------------------+
    |R|                  Last-Stream-ID (31)                        |
    +-+-------------------------------------------------------------+
    |                      Error Code (32)                          |
    +---------------------------------------------------------------+
    |                  Additional Debug Data (*)                    |
    +---------------------------------------------------------------+

"""

from dogu.frame import (Frame, FrameType)
from dogu.util import int_to_bytes
from dogu.http2_exception import ProtocolError

class GoawayFrame(Frame):

    GOAWAY_DEBUG_ENCODING = 'iso-8859-1'

    @classmethod
    def load(cls, frame, header, **kargs):

        # frame length, type, flag, id
        frm_len, frm_type, frm_flag, frm_id = header

        if frm_id is not 0:
            raise ProtocolError('GOAWAY frame id must be 0x0')

        if frm_len < 8:
            raise ProtocolError('GOAWAY frame length must be greater than 8')

        last_stream_id = frame[0] << 24
        last_stream_id += frame[1] << 16
        last_stream_id += frame[2] << 8
        last_stream_id += frame[3]

        error_code = frame[4] << 24
        error_code += frame[5] << 16
        error_code += frame[6] << 8
        error_code += frame[7]

        debug_data = frame[8:(frm_len - 8)].encode(GoawayFrame.GOAWAY_DEBUG_ENCODING)

        goaway_frame = GoawayFrame(last_stream_id, error_code, debug_data)

        return goaway_frame

    def __init__(self, last_stream_id, error_code, debug_data):
        Frame.__init__(
            self,
            type=FrameType.GOAWAY,
            flag=0x0,
            id=0x0,
            data=None
        )

        self.last_stream_id = last_stream_id
        self.error_code = error_code
        self.debug_data = debug_data

    def get_frame_bin(self):

        if self._data is None:
            self._data = bytearray()
            self._data += int_to_bytes(self.last_stream_id, 4)
            self._data += int_to_bytes(self.error_code, 4)

            self._data = self.debug_data.encode(GoawayFrame.GOAWAY_DEBUG_ENCODING)

        return Frame.get_frame_bin(self)
