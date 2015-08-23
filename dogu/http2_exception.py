

class HTTP2Error(Exception):
    def __init__(self, debug_data='', code=0):
        self.code = code
        self.debug_data = debug_data

        Exception.__init__(self)


# The associated condition is not a result of an error.
# For example, a GOAWAY might include this code to indicate graceful shutdown of a connection.
class NoError(HTTP2Error):
    def __init__(self, debug_data=''):
        code = 0
        HTTP2Error.__init__(self, debug_data, code)


# The endpoint detected an unspecific protocol error.
# This error is for use when a more specific error code is not available.
class ProtocolError(HTTP2Error):
    def __init__(self, debug_data=''):
        code = 1
        HTTP2Error.__init__(self, debug_data, code)


# The endpoint encountered an unexpected internal error.
class InternalError(HTTP2Error):
    def __init__(self, debug_data=''):
        code = 2
        HTTP2Error.__init__(self, debug_data, code)


# The endpoint detected that its peer violated the flow-control protocol.
class FlowControlerError(HTTP2Error):
    def __init__(self, debug_data=''):
        code = 3
        HTTP2Error.__init__(self, debug_data, code)


# The endpoint sent a SETTINGS frame but did not receive a response in a timely manner.
# See Section 6.5.3 ("Settings Synchronization").
class SettingsTimeoutError(HTTP2Error):
    def __init__(self, debug_data=''):
        code = 4
        HTTP2Error.__init__(self, debug_data, code)


# The endpoint received a frame after a stream was half-closed.
class StreamClosedError(HTTP2Error):
    def __init__(self, debug_data=''):
        code = 5
        HTTP2Error.__init__(self, debug_data, code)


# The endpoint received a frame with an invalid size.
class FrameSizeError(HTTP2Error):
    def __init__(self, debug_data=''):
        code = 6
        HTTP2Error.__init__(self, debug_data, code)


# The endpoint refused the stream prior to performing any application processing (see Section 8.1.4 for details).
class RefusedStreamError(HTTP2Error):
    def __init__(self, debug_data=''):
        code = 7
        HTTP2Error.__init__(self, debug_data, code)


# Used by the endpoint to indicate that the stream is no longer needed.
class CancelError(HTTP2Error):
    def __init__(self, debug_data=''):
        code = 8
        HTTP2Error.__init__(self, debug_data, code)


# The endpoint is unable to maintain the header compression context for the connection.
class CompressionError(HTTP2Error):
    def __init__(self, debug_data=''):
        code = 9
        HTTP2Error.__init__(self, debug_data, code)


# The connection established in response to a CONNECT request (Section 8.3) was reset or abnormally closed.
class ConnectError(HTTP2Error):
    def __init__(self, debug_data=''):
        code = 10
        HTTP2Error.__init__(self, debug_data, code)


# The endpoint detected that its peer is exhibiting a behavior that might be generating excessive load.
class EnhanceYourCalmSizeError(HTTP2Error):
    def __init__(self, debug_data=''):
        code = 11
        HTTP2Error.__init__(self, debug_data, code)


# The underlying transport has properties that do not meet minimum security requirements (see Section 9.2).
class InadequateSecurityError(HTTP2Error):
    def __init__(self, debug_data=''):
        code = 12
        HTTP2Error.__init__(self, debug_data, code)


# The endpoint requires that HTTP/1.1 be used instead of HTTP/2.
class HTTP1RequiredError(HTTP2Error):
    def __init__(self, debug_data=''):
        code = 13
        HTTP2Error.__init__(self, debug_data, code)
