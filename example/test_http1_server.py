from dogu.server import start, set_server
from flask import Flask
# from gevent import sleep
from flask import request


app = Flask(__name__)

@app.route("/")
def hello():
    print(request.environ)
    return "Hello World!"

@app.route('/upload', methods=["POST"])
def video():
    print(request.files)
    return 'Upload!!'

@app.route('/upload', methods=["GET"])
def upload_video():
    return """
    <html>
    <head>
    </head>
    <body>
        <form method="POST" enctype="multipart/form-data" action="/upload">
            <input type="file" name="video">
            <input type="submit">
        </form>
    </body>
    </html>
    """

server_setting = set_server(
    app=app,
    use_ssl=True,
    crt_file='server.crt',
    key_file='server.key',
    debug=True,
    use_http2=True,
    keep_alive_timeout=40,
    workers=20
)

start([server_setting])
