
import io
from gevent import sleep
from gevent.coros import Semaphore

class DataFrameIO(io.RawIOBase):

    """Raw I/O implementation for stream sockets.

    This class supports the makefile() method on sockets.  It provides
    the raw I/O interface on top of a socket object.
    """

    def __init__(self):
        io.RawIOBase.__init__(self)
        self.buf = bytearray()
        self.target_size = 0
        self.semaphore = Semaphore()
        self._closed = False

    @property
    def closed(self):
        return self._closed

    def readinto(self, b):
        """Read up to len(b) bytes into the writable buffer *b* and return
        the number of bytes read.  If the socket is non-blocking and no bytes
        are available, None is returned.

        If *b* is non-empty, a 0 return value indicates that the connection
        was shutdown at the other end.
        """

        self.target_size = len(b)

        if self.target_size > len(self.buf):
            self.semaphore.acquire()

        b[0:self.target_size] = self.buf[0:self.target_size]
        del self.buf[0:self.target_size]

        return self.target_size

    def write(self, b):
        """Write the given bytes or bytearray object *b* to the socket
        and return the number of bytes written.  This can be less than
        len(b) if not all data could be written.  If the socket is
        non-blocking and no bytes could be written None is returned.
        """

        self.buf += b

        if self.target_size <= len(self.buf):
            self.semaphore.release()

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
        self._closed = True
        self.buf = bytearray()
