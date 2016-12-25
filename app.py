from flask import Flask
from flask import render_template
from flask_socketio import send
from flask_socketio import SocketIO
import json


app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)


@app.route('/')
def index(name=None):
    return render_template('index.html', name=name)


@socketio.on('message')
def handle_message(message):
    print(json.dumps(message))


if __name__ == '__main__':
    socketio.run(app)
