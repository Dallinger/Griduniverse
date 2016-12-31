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
    num_players=3,
    columns=40,
    rows=40,
    block_size=10,
    padding=1,
    respawn_food=True,
    dollars_per_point=0.02,
)

start = time.time()


def game_loop():
    """Update the world state."""
    frame = 0
    while True:
        socketio.sleep(0.010)
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
        socketio.sleep(0.050)
        count += 1
        socketio.emit(
            'state',
            {
                'state_json': grid.serialize(),
                'clients': clients,
                'count': count,
            },
            broadcast=True,
        )

socketio.start_background_task(target=send_state_thread)


@socketio.on('connect')
def test_connect():
    print("Client {} has connected.".format(request.sid))
    client_count = len([c for c in clients if clients is not -1])
    if client_count < grid.num_players:
        clients.append(request.sid)
        grid.spawn_player(id=clients.index(request.sid))


@socketio.on('disconnect')
def test_disconnect():
    print('Client {} has disconnected.'.format(request.sid))
    clients[clients.index(request.sid)] = -1


@app.route('/')
def index():
    return render_template('index.html', grid=grid)


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


@socketio.on('change_color')
def handle_change_color(msg):
    player = grid.players[msg['player']]
    player.color = msg['color']


if __name__ == '__main__':
    socketio.run(app)
