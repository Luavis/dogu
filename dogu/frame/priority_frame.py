"""
    +-+-------------------------------------------------------------+
    |E|                  Stream Dependency (31)                     |
    +-+-------------+-----------------------------------------------+
    |   Weight (8)  |
    +-+-------------+

"""

from dogu.frame import (Frame, FrameType)
from dogu.util import int_to_bytes
from dogu.http2_exception import ProtocolError


class PriorityFrame(Frame):

    @classmethod
    def load(cls, frame, header):

        # frame length, type, flag, id
        frm_len, frm_type, frm_flag, frm_id = header

        if frm_id is 0x0:  # protocol error
            raise ProtocolError("'frm_id must not be 0x0")

        if frm_type is not FrameType.PRIORITY:
            raise ValueError("frame is not type of PRIORITY type")

        start_index = 0  # default is payload stat index

        dep_stream_id = frame[start_index] << 24
        dep_stream_id += frame[start_index + 1] << 16
        dep_stream_id += frame[start_index + 2] << 8
        dep_stream_id += frame[start_index + 3]

        weight = frame[start_index + 4]
        priority_frame = PriorityFrame(frm_id, dep_stream_id, weight)

        return priority_frame

    def __init__(self, id, dep_stream_id, weight):

        self._dependency_id = dep_stream_id
        self._weight = weight

        Frame.__init__(self, type=FrameType.PRIORITY, flag=0x0, id=id, data=None)

    def get_frame_bin(self):

        if self._data is None:  # if user didn't touch data
            self._data = bytearray()
            self._data += int_to_bytes(self._dependency_id)  # append dependency stream id
            self._data.append(self._weight)

        return Frame.get_frame_bin(self)

    def priority(self, dep_stream_id, weight):

        self._is_priority = True

        self._dependency_id = dep_stream_id

        self._weight = weight  # set priority weight
