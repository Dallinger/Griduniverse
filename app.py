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
    columns=25,
    rows=25,
    block_size=10,
    padding=1,
    num_colors=2,
    respawn_food=True,
    mutable_colors=False,
    dollars_per_point=0.02,
    player_overlap=False,
    background_animation=True,
    time=300,
    tax=0.1,
    walls="maze",
    show_grid=True,
    visibility=5,
    speed_limit=8,
    motion_auto=False,
)


def game_loop():
    """Update the world state."""
    previous_tax_timestamp = grid.start_timestamp

    complete = False
    while not complete:

        socketio.sleep(0.010)

        # Update motion.
        if grid.motion_auto:
            for player in grid.players:
                player.move(player.motion_direction)

        # Consume the food.
        grid.consume()

        # Apply tax.
        if (time.time() - previous_tax_timestamp) > 1.000:
            for player in grid.players:
                player.score = max(player.score - grid.tax, 0)
            previous_tax_timestamp = time.time()

        # Check if the game is over.
        if (time.time() - grid.start_timestamp) > grid.time:
            complete = True
            socketio.emit('stop', {}, broadcast=True)


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
                'remaining_time': time.time() - grid.start_timestamp,
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
    player.move(msg['move'])


@socketio.on('change_color')
def handle_change_color(msg):
    player = grid.players[msg['player']]
    player.color = msg['color']


if __name__ == '__main__':
    socketio.run(app)
