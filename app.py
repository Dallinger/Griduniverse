from flask import Flask
from flask import request
from flask import render_template
from flask_socketio import emit
from flask_socketio import send
from flask_socketio import SocketIO
import json


app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)
thread = None


def background_thread():
    """Example of how to send server-generated events to clients."""
    count = 0
    while True:
        socketio.sleep(1)
        count += 1
        socketio.emit(
            'new_data',
            {
                'data': 'Server generated event',
                'count': count
            }
        )


@socketio.on('connect')
def test_connect():
    global thread
    if thread is None:
        socketio.start_background_task(target=background_thread)
    emit('connected', {'data': 'Connected', 'count': 0})


@app.route('/')
def index(name=None):
    return render_template('index.html', name=name)


@socketio.on('message')
def handle_message(message):
    print(json.dumps(message))


@socketio.on('disconnect')
def test_disconnect():
    print('Client disconnected', request.sid)


if __name__ == '__main__':
    socketio.run(app)
