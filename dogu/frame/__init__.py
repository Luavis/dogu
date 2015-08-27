"""
 +-----------------------------------------------+
 |                 Length (24)                   |
 +---------------+---------------+---------------+
 |   Type (8)    |   Flags (8)   |
 +-+-------------+---------------+-------------------------------+
 |R|                 Stream Identifier (31)                      |
 +=+=============================================================+
 |                   Frame Payload (0...)                      ...
 +---------------------------------------------------------------+

"""
from dogu.http2_exception import ProtocolError, FrameSizeError


class FrameType(object):

    DATA = 0x0

    HEADERS = 0x1

    PRIORITY = 0x2

    RST_STREAM = 0x3

    SETTINGS = 0x4

    PUSH_PROMISE = 0x5

    PING = 0x6

    GOAWAY = 0x7

    WINDOW_UPDATE = 0x8

    CONTINUATION = 0x9

DEFAULT_FRAME_MAX_SIZE = 16384


class Frame(object):

    @classmethod
    def parse_header(cls, frame_header):

        if len(frame_header) < 9:
            raise ProtocolError()  # invalid frame

        frame_len = frame_header[0] << 16
        frame_len += frame_header[1] << 8
        frame_len += frame_header[2]

        frame_type = frame_header[3]  # get frame type

        frame_flag = frame_header[4]  # get frame flag

        frame_id = frame_header[5] << 24
        frame_id += frame_header[6] << 16
        frame_id += frame_header[7] << 8
        frame_id += frame_header[8]

        return (frame_len, frame_type, frame_flag, frame_id)

    @classmethod
    def load(cls, frame, header=None, **kargs):

        from dogu.frame.setting_frame import SettingFrame
        from dogu.frame.data_frame import DataFrame
        from dogu.frame.header_frame import HeaderFrame
        from dogu.frame.push_promise_frame import PushPromiseFrame
        from dogu.frame.rst_frame import RSTFrame
        from dogu.frame.window_update import WindowUpdateFrame

        if header is None:
            header = cls.parse_header(frame)

        # frame length, type, flag, id
        frm_len, frm_type, frm_flag, frm_id = header

        frm_cls = None

        # check frame length match real size

        if not frm_len == len(frame):
            raise FrameSizeError()

        if frm_type == FrameType.DATA:
            frm_cls = DataFrame
        elif frm_type == FrameType.SETTINGS:
            frm_cls = SettingFrame
        elif frm_type == FrameType.HEADERS:
            frm_cls = HeaderFrame
        elif frm_type == FrameType.PUSH_PROMISE:
            frm_cls = PushPromiseFrame
        elif frm_type == FrameType.RST_STREAM:
            frm_cls = RSTFrame
        elif frm_type == FrameType.WINDOW_UPDATE:
            frm_cls = WindowUpdateFrame
        else:
            return None

        return frm_cls.load(frame, header, **kargs)

    def __init__(
            self,
            type=FrameType.DATA,
            flag=0,
            id=0,
            data=bytearray(),
            frame_max_size=DEFAULT_FRAME_MAX_SIZE):

        self._type = type
        self._flag = flag
        self._id_bin = id

        self.max_size = frame_max_size

        # pass if  data is None; for lazy set data

        if data is not None and len(data) > self.max_size:
            raise FrameSizeError()

        self._data = data

    @property
    def data(self):
        return self._data

    @data.setter
    def data(self, value):
        if len(value) > self.max_size:
            raise ValueError('Data size is invalid size')
        else:
            self._data = value

    @property
    def type(self):
        return self._type

    @type.setter
    def type(self, value):
        if value > 0xFF:
            raise ValueError('Type is out of size')
        else:
            self._type = value

    @property
    def flag(self):
        return self._flag

    @property
    def id(self):
        return self._id_bin

    @id.setter
    def id(self, value):
        if value > 0xFFFFFFFF or not(value & 0x7FFFFFFF == value):
            raise ValueError('ID is invalid')
        else:
            self._id_bin = value

    def get_frame_bin(self):

        ret_bin = bytearray()

        # append length field
        self._append_length_bin(ret_bin)

        # append type field
        self._append_type_bin(ret_bin)

        # append flag field
        self._append_flag_bin(ret_bin)

        # append stream identification field
        self._append_id_bin(ret_bin)

        # append payload data
        for d in self._data:
            ret_bin.append(d)

        return ret_bin

    def _append_length_bin(self, ret_bin):

        len_bin = len(self._data)

        ret_bin.append((len_bin & 0xFF0000) >> 16)

        ret_bin.append((len_bin & 0x00FF00) >> 8)

        ret_bin.append((len_bin & 0x0000FF) >> 0)

    def _append_type_bin(self, ret_bin):

        type_bin = self._type

        ret_bin.append(type_bin & 0xFF)

    def _append_flag_bin(self, ret_bin):

        flag_bin = self._flag

        ret_bin.append(flag_bin & 0xFF)

    def _append_id_bin(self, ret_bin):

        id_bin = 0x7FFFFFFF & self._id_bin

        ret_bin.append((id_bin & 0xFF000000) >> 24)

        ret_bin.append((id_bin & 0x00FF0000) >> 16)

        ret_bin.append((id_bin & 0x0000FF00) >> 8)

        ret_bin.append((id_bin & 0x000000FF) >> 0)
