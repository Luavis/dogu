"""
    dogu.connection
    ~~~~~~~

"""
import sys

from hpack.hpack import Encoder, Decoder


class HTTPConnection(object):

    def __init__(self, is_http2, remote_addr, server_setting, app_list, rfile, wfile):
        self.is_http2 = is_http2
        self.server_setting = server_setting
        self.rfile = rfile
        self.wfile = wfile
        self.remote_addr = remote_addr

        self.stream_dict = dict()
        self.app_list = app_list
        self.encoder = Encoder()
        self.decoder = Decoder()
        self.error_stream = sys.stderr

        self.use_ssl = self.server_setting['use_ssl']

    def run(self):
        pass

    def write(self, data):
        self.wfile.write(data)

    def flush(self):
        self.wfile.flush()

    def read(self, size):
        return self.rfile.read(size)

    def get_app_with_host(self, host):
        try:
            domain = host.split(':')[0]
            app = self.app_list.get(domain)
        except:
            app = None

        if app is None:  # can not find app by domain
            app = self.app_list.get('default')  # find default

            if app is None:
                raise ValueError('unknown domain')  # TODO catch error

        return app
