"""
    dogu.server
    ~~~~~~~

"""
import socket
from threading import Thread
from gevent.queue import Queue
from gevent import spawn
from gevent import monkey
from dogu.connection import HTTPConnection

import ssl


PREFACE_CODE = b"\x50\x52\x49\x20\x2a\x20\x48\x54\x54\x50\x2f\x32\x2e\x30\x0d\x0a\x0d\x0a\x53\x4d\x0d\x0a\x0d\x0a"
PREFACE_SIZE = len(PREFACE_CODE)

monkey.patch_socket()


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
        self.app_list['server_name'] = app

    def run(self):
        if self.use_ssl:
            # TODO: it will not work in below 2.7.9 and 3.2
            ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)

            # TODO : use alpn when it supported
            ssl_context.set_npn_protocols(['h2'])

            ssl_context.load_cert_chain(
                certfile=self.setting['crt_file'],
                keyfile=self.setting['key_file']
            )

            self.listen_sock = ssl_context.wrap_socket(
                socket.socket(socket.AF_INET, socket.SOCK_STREAM),
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
            conn, addr = self.listen_sock.accept()

            if conn is None:
                continue

            self.connection_queue.put((conn, addr))

    def create_workers(self):
        self.connection_queue = Queue()

        for i in range(self.setting['threads']):
            spawn(self.process_tcp_connection)

    def process_tcp_connection(self):
        while True:
            is_http2 = False

            tcp_connection, remote_addr = self.connection_queue.get()

            rfile = tcp_connection.makefile('rb', self.setting['input_buffer_size'])

            wfile = tcp_connection.makefile('wb', self.setting['output_buffer_size'])

            preface = rfile.peek(PREFACE_SIZE)

            is_http2 = (preface[0:PREFACE_SIZE] == PREFACE_CODE)

            if is_http2:
                rfile.read(PREFACE_SIZE)  # read left

            connection = HTTPConnection(is_http2, remote_addr, self.server_setting, rfile, wfile)

            if not self.server_setting['debug']:
                try:
                    connection.run()
                except:
                    pass  # TODO : stack error log
            else:
                connection.run()


def set_server(
        host='127.0.0.1',
        port=2043,
        server_name='',
        app=None,
        threads=1,
        process=1,
        input_buffer_size=1000,
        output_buffer_size=1000,
        keep_alive=True,
        keep_alive_timeout=45,
        use_ssl=False,
        crt_file="",
        key_file="",
        debug=False):
    """
    This function is wrapping dogu interface application to run with specific settings
    """
    if app is None:
        raise ValueError()

    if not hasattr(app, '__call__'):
        raise ValueError()

    server_setting = dict()

    server_setting["host"] = host
    server_setting["port"] = port
    server_setting["threads"] = threads
    server_setting["process"] = process
    server_setting["input_buffer_size"] = input_buffer_size
    server_setting["output_buffer_size"] = output_buffer_size
    server_setting["keep_alive"] = keep_alive
    server_setting["keep_alive_timeout"] = keep_alive_timeout
    server_setting["use_ssl"] = use_ssl
    server_setting["crt_file"] = crt_file
    server_setting["key_file"] = key_file

    server_setting['app'] = app
    server_setting['debug'] = debug

    return server_setting


def start(server_settings):

    server_list = dict()

    for server_setting in server_settings:

        server_name = server_setting['host'] + ':' + str(server_setting['port'])

        server = server_list.get(server_name)

        if server is None:
            server_list[server_name] = Server(
                server_setting
            )

        server_list[server_name].register(server_name, server_setting['app'])

    for server_name, server in server_list.items():
        server.run()
