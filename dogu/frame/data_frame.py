"""
    +---------------+
    |Pad Length? (8)|
    +---------------+-----------------------------------------------+
    |                            Data (*)                         ...
    +---------------------------------------------------------------+
    |                           Padding (*)                       ...
    +---------------------------------------------------------------+

"""

from dogu.frame import (Frame, FrameType)
from dogu.http2_exception import ProtocolError


class DataFrame(Frame):

    PAD_MAX_LENGTH = 255

    # HEADERS frame flags

    END_STREAM_FLAG = 0x1

    PADDED_FLAG = 0x8

    @classmethod
    def load(cls, frame, header, **kargs):

        # frame length, type, flag, id
        frm_len, frm_type, frm_flag, frm_id = header

        if frm_id is 0x0:  # protocol error
            raise ProtocolError()

        if frm_type is not FrameType.DATA:
            raise ValueError("frame is not type of DATA type")

        end_stream = False

        data_start_index = 0  # default is payload stat index
        data_pad_length = 0

        if frm_flag & DataFrame.END_STREAM_FLAG is not 0:
            end_stream = True

        # create header frame to return
        data_frame = cls(frm_id, end_stream)

        if frm_flag & DataFrame.PADDED_FLAG is not 0:  # if it is padded
            data_pad_length = frame[data_start_index]
            data_start_index += 1  # if padded, first byte is pad length

        # create data block

        data_end_index = 9 + frm_len - data_pad_length

        # get header block

        data_block = frame[data_start_index:data_end_index]
        data_frame.data = data_block

        return data_frame

    def __init__(self, id, end_stream=False):

        self.is_end_stream = end_stream

        self._is_padded = False

        Frame.__init__(self, type=FrameType.DATA, flag=0x0, id=id)

    def set_text(self, text, encoding='iso-8859-1'):
        self._data = text.encode(encoding)

    def get_frame_bin(self):

        headers_frame_field = bytearray()

        if self._data is None:
            self._data = bytearray()  # check for safe

        self._flag = self.flag  # get flag by method

        if self._is_padded:

            headers_frame_field.append(self._pad_len)  # append pad length

            self._data += bytearray(self._pad_len)  # append pad byte in pad length

        self._data = headers_frame_field + self._data  # append HEADERS field

        return Frame.get_frame_bin(self)

    @property
    def flag(self):
        flag = 0x0

        if self.is_end_stream:
            flag |= DataFrame.END_STREAM_FLAG

        if self._is_padded:
            flag |= DataFrame.PADDED_FLAG

        return flag

    def padding(self, pad_len):

        if pad_len > DataFrame.PAD_MAX_LENGTH:  # padding length error
            raise ValueError("pad_len is greater then pad max length")

        self._flag |= DataFrame.PADDED_FLAG  # flag padded
        self._is_padded = True
        self._pad_len = pad_len
