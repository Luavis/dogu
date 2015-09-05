"""
    dogu.server
    ~~~~~~~

"""
import socket
from threading import Thread
from gevent.queue import Queue
from gevent import spawn
from gevent import monkey
from dogu.frame.setting_frame import SettingFrame
from dogu.connection.http1 import HTTP1Connection
from dogu.connection.http2 import HTTP2Connection
from dogu.logger import logger

import ssl


PREFACE_CODE = b'\x50\x52\x49\x20\x2a\x20\x48\x54\x54\x50\x2f\x32\x2e\x30\x0d\x0a\x0d\x0a\x53\x4d\x0d\x0a\x0d\x0a'
SERVER_PREFACE = b'\x00\x00\x00\x04\x01\x00\x00\x00\x00'
PREFACE_SIZE = len(PREFACE_CODE)

monkey.patch_all()


class Server(Thread):

    def __init__(self, setting):
        self.listen_sock = None

        # cache settings

        self.host = setting['host']
        self.port = setting['port']
        self.use_ssl = setting['use_ssl']
        self.setting = setting

        # create app list

        self.app_list = dict()

    def register(self, server_name, app):
        self.app_list[server_name] = app

    def run(self):
        if self.use_ssl:
            if hasattr(ssl, 'SSLContext'):
                if hasattr(ssl, 'PROTOCOL_TLSv1_2'):
                    # TODO: it will not work in below 2.7.9 and 3.2
                    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
                else:
                    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLSv1)

                if self.setting['use_http2']:
                    protocol_nego = None

                    if hasattr(ssl, 'HAS_NPN'):
                        if ssl.HAS_NPN:
                            protocol_nego = 'NPN'
                            ssl_context.set_npn_protocols(['h2'])
                    if hasattr(ssl, 'HAS_ALPN'):
                        if ssl.HAS_ALPN:
                            protocol_nego = 'ALPN'
                            ssl_context.set_alpn_protocols(['h2'])

                    if protocol_nego is None:
                        logger.info('Unsupport NPN or ALPN')

                ssl_context.load_cert_chain(
                    certfile=self.setting['crt_file'],
                    keyfile=self.setting['key_file']
                )

                self.listen_sock = ssl_context.wrap_socket(
                    socket.socket(socket.AF_INET, socket.SOCK_STREAM),
                    server_side=True
                )
            else:
                logger.info('Unsupport NPN or ALPN')
                self.listen_sock = ssl.wrap_socket(
                    socket.socket(socket.AF_INET, socket.SOCK_STREAM),
                    certfile=self.setting['crt_file'],
                    keyfile=self.setting['key_file'],
                    ssl_version=ssl.PROTOCOL_TLSv1,
                    server_side=True
                )
        else:
            self.listen_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        self.listen_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        self.listen_sock.bind((self.host, self.port))

        self.listen_sock.listen(5)

        # create workers which process connections
        self.create_workers()

        while True:
            try:
                conn, addr = self.listen_sock.accept()
                if conn is None:
                    continue

                self.connection_queue.put((conn, addr))
            except ssl.SSLError:
                logger.debug('user access in tls connection without ssl cert')

    def create_workers(self):
        self.connection_queue = Queue()

        for i in range(self.setting['workers']):
            spawn(self.process_tcp_connection)

    def default_setting(self):
        frame = SettingFrame()
        frame.set(SettingFrame.SETTINGS_INITIAL_WINDOW_SIZE, 16777215)
        frame.set(SettingFrame.SETTINGS_MAX_FRAME_SIZE, 16777215)

        return frame

    def process_tcp_connection(self):
        while True:
            is_http2 = False
            tcp_connection, remote_addr = self.connection_queue.get()
            tcp_connection.settimeout(self.setting['keep_alive_timeout'])
            rfile = tcp_connection.makefile('rb', self.setting['input_buffer_size'])
            wfile = tcp_connection.makefile('wb', self.setting['output_buffer_size'])

            try:
                preface = rfile.peek(PREFACE_SIZE)
            except socket.timeout:
                self.close_connection(tcp_connection)
                continue  # close connection
            except OSError:
                logger.debug('user close connection')
                continue

            is_http2 = (preface[:PREFACE_SIZE] == PREFACE_CODE)

            if is_http2:
                rfile.read(PREFACE_SIZE)  # clean buffer
                frame = self.default_setting()

                wfile.write(frame.get_frame_bin())
                wfile.write(SERVER_PREFACE)

                wfile.flush()

                connection = HTTP2Connection(
                    is_http2,
                    remote_addr,
                    self.setting,
                    self.app_list,
                    rfile,
                    wfile
                )
            else:
                connection = HTTP1Connection(
                    is_http2,
                    remote_addr,
                    self.setting,
                    self.app_list,
                    rfile,
                    wfile
                )

            if not self.setting['debug']:
                try:
                    connection.run()
                except socket.timeout:
                    pass
                except ssl.SSLError:
                    pass
                except:
                    pass  # TODO : stack error log
            else:
                try:
                    connection.run()
                except ssl.SSLError:
                    pass
                except socket.timeout:
                    pass
                except OSError:
                    logger.debug('user close connection')

            self.close_connection(tcp_connection)  # close connection

    def close_connection(self, tcp_connection):
        try:
            tcp_connection.shutdown(socket.SHUT_RDWR)
            tcp_connection.close()
        except OSError:  # if already closed just pass it
            pass

def set_server(
        host='127.0.0.1',
        port=2043,
        server_name='default',
        app=None,
        workers=1,
        process=1,
        input_buffer_size=1000,
        output_buffer_size=1000,
        keep_alive=True,
        keep_alive_timeout=10,
        use_ssl=False,
        crt_file="",
        key_file="",
        debug=False,
        use_http2=True):
    """
    This function is wrapping dogu interface application
    to run with specific settings
    """
    if app is None:
        raise ValueError()

    if not hasattr(app, '__call__'):
        raise ValueError()

    server_setting = dict()

    server_setting['host'] = host
    server_setting['port'] = port
    server_setting['server_name'] = server_name
    server_setting['workers'] = workers
    server_setting['process'] = process
    server_setting['input_buffer_size'] = input_buffer_size
    server_setting['output_buffer_size'] = output_buffer_size
    server_setting['keep_alive'] = keep_alive
    server_setting['keep_alive_timeout'] = keep_alive_timeout
    server_setting['use_ssl'] = use_ssl
    server_setting['crt_file'] = crt_file
    server_setting['key_file'] = key_file
    server_setting['use_http2'] = use_http2

    server_setting['app'] = app
    server_setting['debug'] = debug

    return server_setting


def start(server_settings):

    server_list = dict()

    for server_setting in server_settings:

        logger.info('Run server')

        server_id = server_setting['host'] + ':' + str(server_setting['port'])

        server = server_list.get(server_id)

        if server is None:
            server_list[server_id] = Server(
                server_setting
            )

        server_list[server_id].register(
            server_setting['server_name'],
            server_setting['app']
        )

    for server_name, server in server_list.items():
        server.run()
