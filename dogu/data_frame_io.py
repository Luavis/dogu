
import io
from gevent import sleep


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

        while not min(len(b), len(self.buf)) == len(b):
            sleep(0)

        read_size = min(len(b), len(self.buf))

        b[0:read_size] = self.buf[0:read_size]
        del self.buf[0:read_size]

        return read_size

    def write(self, b):
        """Write the given bytes or bytearray object *b* to the socket
        and return the number of bytes written.  This can be less than
        len(b) if not all data could be written.  If the socket is
        non-blocking and no bytes could be written None is returned.
        """
        self.buf += b

        return len(b)

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
