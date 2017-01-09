from grid import Gridworld

from flask import Flask
from flask import render_template
from flask import request
from flask_socketio import SocketIO

import json
import time

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)

clients = []

grid = Gridworld(
    num_players=10,
    columns=20,
    rows=20,
    block_size=10,
    padding=1,
    num_colors=2,
    respawn_food=True,
    mutable_colors=False,
    dollars_per_point=0.02,
    player_overlap=False,
    background_animation=True,
    time=300,
)

start = time.time()


def game_loop():
    """Update the world state."""
    complete = False
    while not complete:

        socketio.sleep(0.010)

        if (time.time() - start) > grid.time:
            complete = True
            socketio.emit('stop', {}, broadcast=True)

        for player in grid.players:
            if player.motion_auto:
                ts = time.time() - start
                wait_time = 1.0 / player.motion_speed
                if (ts > (player.motion_timestamp + wait_time)):
                    player.move(player.motion_direction, grid=grid)
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
                'remaining_time': time.time() - start,
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
    player.move(msg['move'], grid=grid)


@socketio.on('change_color')
def handle_change_color(msg):
    player = grid.players[msg['player']]
    player.color = msg['color']


if __name__ == '__main__':
    socketio.run(app)
