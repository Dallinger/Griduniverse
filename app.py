from grid import Gridworld

from flask import Flask
from flask import render_template
from flask import request
from flask_socketio import SocketIO

import math
import time

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)

clients = []

grid = Gridworld(
    num_players=8,
    num_food=8,
    columns=25,
    rows=25,
    block_size=10,
    padding=1,
    num_colors=2,
    respawn_food=True,
    food_visible=True,
    mutable_colors=False,
    dollars_per_point=0.02,
    initial_score=50,
    player_overlap=False,
    background_animation=True,
    time=300,
    tax=0,
    walls=None,
    show_grid=True,
    visibility=1000,
    speed_limit=8,
    motion_auto=False,
    motion_cost=0,
    motion_tremble_rate=0.00,
    frequency_dependence=0,
    frequency_dependent_payoff_rate=1,
    chatroom=True,
    contagion=0,
    contagion_hierarchy=False,
    donation=1,
    pseudonyms=False,
    pseudonyms_locale="it_IT",
)


def game_loop():
    """Update the world state."""
    previous_second_timestamp = grid.start_timestamp

    complete = False
    while not complete:

        socketio.sleep(0.010)

        now = time.time()

        # Update motion.
        if grid.motion_auto:
            for player in grid.players:
                player.move(player.motion_direction, tremble_rate=0)

        # Consume the food.
        grid.consume()

        # Spread through contagion.
        if grid.contagion > 0:
            grid.spread_contagion()

        # Trigger time-based events.
        if (now - previous_second_timestamp) > 1.000:

            for player in grid.players:
                # Apply tax.
                player.score = max(player.score - grid.tax, 0)

                # Apply frequency-dependent payoff.
                for player in grid.players:
                    abundance = len(
                        [p for p in grid.players if p.color == player.color]
                    )
                    relative_frequency = 1.0 * abundance / len(grid.players)
                    payoff = fermi(
                        beta=grid.frequency_dependence,
                        p1=relative_frequency,
                        p2=0.5
                    ) * grid.frequency_dependent_payoff_rate

                    player.score = max(player.score + payoff, 0)

            previous_second_timestamp = now

        # Check if the game is over.
        if (now - grid.start_timestamp) > grid.time:
            complete = True
            socketio.emit('stop', {}, broadcast=True)


socketio.start_background_task(target=game_loop)


def fermi(beta, p1, p2):
    """The Fermi function from statistical physics."""
    return 2.0 * ((1.0 / (1 + math.exp(-beta * (p1 - p2)))) - 0.5)


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
def handle_message(msg):
    socketio.emit('message', msg, broadcast=True)


@socketio.on('move')
def handle_move(msg):
    player = grid.players[msg['player']]
    player.move(msg['move'], tremble_rate=player.motion_tremble_rate)


@socketio.on('change_color')
def handle_change_color(msg):
    player = grid.players[msg['player']]
    player.color = msg['color']


@socketio.on('donate')
def handle_donate(msg):
    """Send a donation from one player to another."""
    player_to = grid.players[msg['player_to']]
    player_from = grid.players[msg['player_from']]
    donation = msg['amount']

    if player_from.score >= donation:

        player_from.score -= donation
        player_to.score += donation

        socketio.emit(
            'donate', {
                'player_from': player_from.id,
                'player_to': player_to.id,
                'donation': donation,
            },
            room=clients[player_to.id]
        )


if __name__ == '__main__':
    socketio.run(app)
