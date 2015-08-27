"""
    +-------------------------------+
    |       Identifier (16)         |
    +-------------------------------+-------------------------------+
    |                        Value (32)                             |
    +---------------------------------------------------------------+

"""

from dogu.frame import (Frame, FrameType)
from dogu.http2_exception import ProtocolError
from dogu.logger import logger

class SettingFrame(Frame):

    ACK_FLAG = 0x1

    # setting identifier

    SETTINGS_HEADER_TABLE_SIZE = 0x1

    SETTINGS_ENABLE_PUSH = 0x2

    SETTINGS_MAX_CONCURRENT_STREAMS = 0x3

    SETTINGS_INITIAL_WINDOW_SIZE = 0x4

    SETTINGS_MAX_FRAME_SIZE = 0x5

    SETTINGS_MAX_HEADER_LIST_SIZE = 0x6

    SETTINGS_RANGE = range(1, 7)  # range from 1 to 6

    @classmethod
    def load(cls, frame, header, **kargs):

        logger.debug('recv settings frame %s',  frame)

        # frame length, type, flag, id
        frm_len, frm_type, frm_flag, frm_id = header

        if frm_id is not 0x0:  # protocol error
            raise ProtocolError("'frm_id must be 0x0")

        if frm_type is not FrameType.SETTINGS:
            raise ValueError("frame is not type of SETTINGS type")

        if frm_flag == SettingFrame.ACK_FLAG and frm_len is not 0:  # protocol error
            raise ProtocolError("Frame is ACK frame but frame length is not 0")

        setting_frame = cls()

        # check frame flag
        if frm_flag == SettingFrame.ACK_FLAG:
            setting_frame.is_ack = True

        if frm_len is not 0:  # parsing setting list
            index = 0  # first frame payload index

            try:  # check for out of index
                while index < frm_len:  # index default value was 9

                    setting_id = frame[index] << 8
                    setting_id += frame[index + 1]  # read setting id 16 bit

                    # read setting value 32 bit
                    setting_value = frame[index + 2] << 24
                    setting_value += frame[index + 3] << 16
                    setting_value += frame[index + 4] << 8
                    setting_value += frame[index + 5]

                    if setting_id in SettingFrame.SETTINGS_RANGE:  # ignore if setting id is not in range
                        setting_frame._setting_list.append((setting_id, setting_value))

                    index += 6  # read 6 byte more for next reading
            except IndexError:
                raise ProtocolError("frame payload is out of format")

        return setting_frame

    def __init__(self, is_ack=False):

        self._setting_list = []
        self.is_ack = is_ack  # is frame ACK SETTINGS frame

        Frame.__init__(self, type=FrameType.SETTINGS, flag=0x0, id=0x0, data=None)

    @property
    def setting_list(self):
        return self._setting_list

    def set(self, setting_id, val=0x0):
        if self.is_ack:
            raise Exception("this SETTINGS frame is ACK SETTINGS")

        self._setting_list.append((setting_id, val))

    def get(self, setting_id):

        for setting in self._setting_list:
            if setting[0] == setting_id:
                return setting[1]

        return None  # if setting is not defined return None

    def get_frame_bin(self):

        if self._data is None and not self.is_ack:  # If user didn't set data

            self._data = bytearray()

            for setting in self._setting_list:

                # set identifier 16 bit

                self._data.append((setting[0] & 0x0000FF00) >> 8)

                self._data.append((setting[0] & 0x000000FF) >> 0)

                # set value 32 bit

                self._data.append((setting[1] & 0xFF000000) >> 24)

                self._data.append((setting[1] & 0x00FF0000) >> 16)

                self._data.append((setting[1] & 0x0000FF00) >> 8)

                self._data.append((setting[1] & 0x000000FF) >> 0)

        elif self.is_ack:  # if ACK SETTINGS frame clear payload
            self._data = bytearray()
            self._flag = SettingFrame.ACK_FLAG

        # call super get_frame_bin

        return Frame.get_frame_bin(self)
