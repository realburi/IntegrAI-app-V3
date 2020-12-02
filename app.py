#-*- coding:utf-8 -*-

from flask_socketio import SocketIO, emit
from flask_cors import CORS
from flask import Flask

from ui import UI

if __name__ != '__main__':
    from ui import DET_Handler

PORT = 9000
app = Flask(__name__)
app.register_blueprint(UI, url_prefix='/')

CORS(app)
UISocket = SocketIO(app)
UIthread = None


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT, threaded=True, debug=False)
