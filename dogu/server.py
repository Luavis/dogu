"""
    dogu.server
    ~~~~~~~

"""
import socket
from threading import Thread
import ssl

try:  # for py3
    from queue import Queue
except ImportError:  # for py2
    import Queue

PREFACE_CODE = b"\x50\x52\x49\x20\x2a\x20\x48\x54\x54\x50\x2f\x32\x2e\x30\x0d\x0a\x0d\x0a\x53\x4d\x0d\x0a\x0d\x0a"
PREFACE_SIZE = len(PREFACE_CODE)


class Server(Thread):

    def __init__(self, setting):
        self.listen_sock = None

        # cache settings

        self.host = setting['host']
        self.port = setting['port']
        self.use_ssl = setting['use_ssl']

        # create app list

        self.app_list = dict()

    def register(self, server_name, app):
        self.app_list['server_name'] = app

    def run(self):

        # override
        Thread.run(self)

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

        self.listen_sock.bind((self.host, self.port))

        # create workers which process connections
        self.create_workers()

        while True:
            conn, addr = self.listen_sock.accept()

            if conn is None:
                continue

            self.connection_queue.put(conn)

    def create_workers(self):
        self.connection_queue = Queue()

        for i in range(self.setting['threads']):
            t = Thread(target=self.process_connection)
            t.daemon = True
            t.start()

    def process_connection(self):
        while True:
            is_connection_http2 = False

            rfile = self.connection.makefile('rb', self.input_buffer_size)

            wfile = self.connection.makefile('rb', self.output_buffer_size)

            preface = rfile.peek(PREFACE_SIZE)

            is_connection_http2 = (preface[0:PREFACE_SIZE] == PREFACE_CODE)

            if is_connection_http2:
                pass


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
        key_file=""):
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

    return server_setting


def start(apps):

    server_list = dict()

    for app in apps:
        server = server_list.get(app['host'] + ':' + str(app['port']))

        if server is None:
            server_list.set(app['host'] + ':' + str(app['port']), Server(app['host'], app['port']))

        server_list.register(app)

    for server in server_list:
        server.run()
