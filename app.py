from grid import (
    Food,
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

clients = []

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
    Player(
        id=0,
        position=[0, 0],
        color=[0.50, 0.86, 1.00],
        motion_auto=False,
        motion_direction="right",
        motion_speed=8,
        motion_timestamp=0
    ),
    Player(
        id=1,
        position=[5, grid.columns - 5],
        color=[1.00, 0.86, 0.50],
        motion_auto=False
    ),
]

grid.food = [
    Food(id=0, position=[10, 10]),
    Food(id=1, position=[5, 5]),
]

start = time.time()


def game_loop():
    """Update the world state."""
    frame = 0
    while True:
        socketio.sleep(0.100)
        frame += 1
        for player in grid.players:
            if player.motion_auto:
                ts = time.time() - start
                wait_time = 1.0 / player.motion_speed
                if (ts > (player.motion_timestamp + wait_time)):
                    player.move(
                        player.motion_direction,
                        rows=grid.rows,
                        columns=grid.columns)
                    player.motion_timestamp = ts

        grid.consume()


socketio.start_background_task(target=game_loop)


def send_state_thread():
    """Example of how to send server-generated events to clients."""
    count = 0
    while True:
        socketio.sleep(0.100)
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
    print("Client {} has connected.".format(request.sid))
    clients.append(request.sid)


@socketio.on('disconnect')
def test_disconnect():
    print('Client {} has disconnected.'.format(request.sid))
    clients[clients.index(request.sid)] = -1



@app.route('/')
def index():
    return render_template('index.html')


@socketio.on('message')
def handle_message(message):
    print(json.dumps(message))


@socketio.on('move')
def handle_move(msg):
    player = grid.players[msg['player']]
    player.move(
        msg['move'],
        rows=grid.rows,
        columns=grid.columns)


if __name__ == '__main__':
    socketio.run(app)
