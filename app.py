from grid import (
    Gridworld,
    Player,
)

from flask import Flask
from flask import render_template
from flask import request
from flask_socketio import emit
from flask_socketio import send
from flask_socketio import SocketIO

import json
import time

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)

grid = Gridworld(
    num_players=2,
    columns=20,
    rows=20,
    grid_block_size=15,
    grid_padding=1,
    respawn_food=True,
    dollars_per_point=0.02,
)

grid.players = [
    Player(id=0, position=[0, 0]),
    Player(id=1, position=[5, grid.columns - 5]),
]


def update_physics_thread():
    """Update the world state."""
    frame = 0
    while True:
        socketio.sleep(0.100)
        frame += 1
        grid.consume()


socketio.start_background_task(target=update_physics_thread)


def send_state_thread():
    """Example of how to send server-generated events to clients."""
    count = 0
    while True:
        socketio.sleep(1.00)
        count += 1
        socketio.emit(
            'state',
            {
                'state_json': grid.serialize(),
                'count': count,
            },
            broadcast=True,
        )

socketio.start_background_task(target=send_state_thread)


@socketio.on('connect')
def test_connect():
    emit('connected', {'data': 'Connected', 'count': 0})


@app.route('/')
def index(name=None):
    return render_template('index.html', name=name)


@socketio.on('message')
def handle_message(message):
    print(json.dumps(message))


@socketio.on('move')
def handle_move(msg):
    grid.players[msg['player']].move(
        msg['move'],
        rows=grid.rows,
        columns=grid.columns)


@socketio.on('disconnect')
def test_disconnect():
    print('Client disconnected', request.sid)


if __name__ == '__main__':
    socketio.run(app)
