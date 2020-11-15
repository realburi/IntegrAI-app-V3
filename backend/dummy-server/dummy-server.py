from flask import Flask, send_file, send_from_directory
import os
from random import choice

app = Flask(__name__)


@app.route("/<string:device_id>")
def index(device_id):
    img_dir = "./backend/dummy-server/static/img"
    img_dir_files = os.listdir(img_dir) 
    return send_file("static/img/" + choice(img_dir_files))


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5432, debug=True)