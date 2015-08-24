
import io


class DataFrameIO(io.RawIOBase):

    """Raw I/O implementation for stream sockets.

    This class supports the makefile() method on sockets.  It provides
    the raw I/O interface on top of a socket object.
    """

    def __init__(self):
        io.RawIOBase.__init__(self)
        self.buf = bytearray()

    @property
    def closed(self):
        return False

    def readinto(self, b):
        """Read up to len(b) bytes into the writable buffer *b* and return
        the number of bytes read.  If the socket is non-blocking and no bytes
        are available, None is returned.

        If *b* is non-empty, a 0 return value indicates that the connection
        was shutdown at the other end.
        """

        b_len = len(b)
        buf_len = len(self.buf)
        read_size = 0

        for i in range(b_len):
            if buf_len - i == 0:
                return read_size

            b[i] = self.buf[0]
            del self.buf[0]
            read_size += 1

        return read_size

    def write(self, b):
        """Write the given bytes or bytearray object *b* to the socket
        and return the number of bytes written.  This can be less than
        len(b) if not all data could be written.  If the socket is
        non-blocking and no bytes could be written None is returned.
        """

        written_len = 0

        for byte in b:
            self.buf.append(byte)
            written_len += 1

        return written_len

    def readable(self):

        return True

    def writable(self):

        return True

    def seekable(self):

        return False

    def fileno(self):
        return None

    def close(self):
        io.RawIOBase.close(self)
        self.buf = bytearray()
