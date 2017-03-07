"""The Griduniverse."""

import json
import math
import os
import random
import time
import uuid

from faker import Factory
from flask import (
    abort,
    Blueprint,
    jsonify,
    render_template,
    request,
)
from flask_socketio import SocketIO
from sqlalchemy import create_engine
from sqlalchemy.orm import (
    sessionmaker,
    scoped_session,
)

import dallinger


config = dallinger.config.get_config()

socketio = SocketIO(logger=True, engineio_logger=True)


class Gridworld(object):
    """A Gridworld in the Griduniverse."""
    player_color_names = [
        "BLUE",
        "YELLOW",
        "RED",
    ]
    player_colors = [
        [0.50, 0.86, 1.00],
        [1.00, 0.86, 0.50],
        [0.64, 0.11, 0.31],
    ]

    GREEN = [0.51, 0.69, 0.61]
    WHITE = [1.00, 1.00, 1.00]

    def __init__(self, **kwargs):
        super(Gridworld, self).__init__()

        self.players = []
        self.food = []
        self.food_consumed = []

        self.num_players = kwargs.get('num_players', 4)
        self.columns = kwargs.get('columns', 25)
        self.rows = kwargs.get('rows', 25)
        self.block_size = kwargs.get('block_size', 15)
        self.padding = kwargs.get('padding', 1)
        self.num_food = kwargs.get('num_food', self.num_players - 1)
        self.food_visible = kwargs.get('food_visible')
        self.food_pg_multiplier = kwargs.get('food_pg_multiplier')
        self.respawn_food = kwargs.get('respawn_food', True)
        self.dollars_per_point = kwargs.get('dollars_per_point', 0.02)
        self.num_colors = kwargs.get('num_colors', 2)
        self.mutable_colors = kwargs.get('mutable_colors', False)
        self.costly_colors = kwargs.get('costly_colors', False)
        self.player_overlap = kwargs.get('player_overlap', True)
        self.background_animation = kwargs.get('background_animation', True)
        self.time = kwargs.get('time', 300)
        self.tax = kwargs.get('tax', 0.01)
        self.wall_type = kwargs.get('walls', None)
        self.walls_visible = kwargs.get('walls_visible', True)
        self.show_grid = kwargs.get('show_grid', None)
        self.visibility = kwargs.get('visibility', 5)
        self.motion_auto = kwargs.get('motion_auto', False)
        self.speed_limit = kwargs.get('speed_limit', 8)
        self.start_timestamp = kwargs.get('start_timestamp', time.time())
        self.motion_cost = kwargs.get('motion_cost', 0)
        self.initial_score = kwargs.get('initial_score', 0)
        self.motion_tremble_rate = kwargs.get('motion_tremble_rate', 0)
        self.frequency_dependence = kwargs.get('frequency_dependence', 0)
        self.frequency_dependent_payoff_rate = kwargs.get(
            'frequency_dependent_payoff_rate', 1)
        self.chatroom = kwargs.get('chatroom', False)
        self.contagion = kwargs.get('contagion', False)
        self.contagion_hierarchy = kwargs.get('contagion_hierarchy', False)
        self.donation = kwargs.get('donation', 0)
        self.pseudonyms = kwargs.get('pseudonyms', False)
        self.pseudonyms_locale = kwargs.get('pseudonyms_locale', 'en_US')
        self.pseudonyms_gender = kwargs.get('pseudonyms_gender', None)
        self.food_reward = kwargs.get('food_reward', 1)
        self.food_growth_rate = kwargs.get('food_growth_rate', 1)
        self.relative_deprivation = kwargs.get('relative_deprivation', 1)

        self.walls = self.generate_walls(style=self.wall_type)

        self.public_good = (
            (self.food_reward * self.food_pg_multiplier) / self.num_players
        )

        for i in range(self.num_food):
            self.spawn_food()

        if self.contagion_hierarchy:
            self.contagion_hierarchy = range(self.num_colors)
            random.shuffle(self.contagion_hierarchy)

        if self.costly_colors:
            self.color_costs = [2**i for i in range(self.num_colors)]
            random.shuffle(self.color_costs)

    def serialize(self):
        return json.dumps({
            "players": [player.serialize() for player in self.players],
            "food": [food.serialize() for food in self.food],
            "walls": [wall.serialize() for wall in self.walls],
        })

    def consume(self):
        """Players consume the food."""
        for food in self.food:
            for player in self.players:
                if food.position == player.position:
                    # Update existence and count of food.
                    self.food_consumed.append(food)
                    self.food.remove(food)
                    if self.respawn_food:
                        self.spawn_food()
                    else:
                        self.num_food -= 1

                    # Update scores.
                    print(player.color_idx)
                    if player.color_idx > 0:
                        reward = self.food_reward
                    else:
                        reward = self.food_reward * self.relative_deprivation

                    player.score += reward
                    for player_to in self.players:
                        player_to.score += self.public_good
                    break

    def spawn_food(self):
        """Respawn the food."""
        self.food.append(Food(
            id=(len(self.food) + len(self.food_consumed)),
            position=self._random_empty_position(),
            color=Gridworld.WHITE,
        ))

    def spawn_player(self, id=None):
        """Spawn a player."""
        player = Player(
            id=id,
            position=self._random_empty_position(),
            num_possible_colors=self.num_colors,
            speed_limit=self.speed_limit,
            motion_cost=self.motion_cost,
            score=self.initial_score,
            motion_tremble_rate=self.motion_tremble_rate,
            pseudonym_locale=self.pseudonyms_locale,
            pseudonym_gender=self.pseudonyms_gender,
            grid=self,
        )
        self.players.append(player)

    def generate_walls(self, style=None):
        """Generate the walls."""
        if style is None:
            walls = []
        elif style is "maze":
            maze = generate_maze(columns=self.columns, rows=self.rows)
            walls = []
            for w in maze:
                walls.append(Wall(position=[w[0], w[1]]))

        return walls

    def _random_empty_position(self):
        """Select an empty cell at random."""
        empty_cell = False
        while (not empty_cell):
            position = [
                random.randint(0, self.rows - 1),
                random.randint(0, self.columns - 1),
            ]
            empty_cell = self._empty(position)

        return position

    def _empty(self, position):
        """Determine whether a particular cell is empty."""
        return not (
            self._has_player(position) or
            self._has_food(position) or
            self._has_wall(position)
        )

    def _has_player(self, position):
        for player in self.players:
            if player.position == position:
                return True
        return False

    def _has_food(self, position):
        for food in self.food:
            if food.position == position:
                return True
        return False

    def _has_wall(self, position):
        for wall in self.walls:
            if wall.position == position:
                return True
        return False

    def spread_contagion(self):
        """Spread contagion."""
        color_updates = []
        for player in self.players:
            colors = [n.color for n in player.neighbors(d=self.contagion)]
            if colors:
                colors.append(player.color)
                plurality_color = max(colors, key=colors.count)
                if colors.count(plurality_color) > len(colors) / 2.0:
                    if (self.rank(plurality_color) < self.rank(player.color)):
                        color_updates.append((player, plurality_color))

        for (player, color) in color_updates:
            player.color = color

    def rank(self, color):
        """Where does this color fall on the color hierarchy?"""
        if self.contagion_hierarchy:
            return self.contagion_hierarchy[
                Gridworld.player_colors.index(color)]
        else:
            return 1


class Food(object):
    """Food."""
    def __init__(self, **kwargs):
        super(Food, self).__init__()

        self.id = kwargs.get('id', uuid.uuid4())
        self.position = kwargs.get('position', [0, 0])
        self.color = kwargs.get('color', [0.5, 0.5, 0.5])

    def serialize(self):
        return {
            "id": self.id,
            "position": self.position,
            "color": self.color,
        }


class Wall(object):
    """Wall."""
    def __init__(self, **kwargs):
        super(Wall, self).__init__()

        self.position = kwargs.get('position', [0, 0])
        self.color = kwargs.get('color', [0.5, 0.5, 0.5])

    def serialize(self):
        return {
            "position": self.position,
            "color": self.color,
        }


class Player(object):
    """A player."""

    def __init__(self, **kwargs):
        super(Player, self).__init__()

        self.id = kwargs.get('id', uuid.uuid4())
        self.position = kwargs.get('position', [0, 0])
        self.motion_auto = kwargs.get('motion_auto', False)
        self.motion_direction = kwargs.get('motion_direction', 'right')
        self.speed_limit = kwargs.get('speed_limit', 8)
        self.num_possible_colors = kwargs.get('num_possible_colors', 2)
        self.motion_cost = kwargs.get('motion_cost', 0)
        self.motion_tremble_rate = kwargs.get('motion_tremble_rate', 0)
        self.grid = kwargs.get('grid', None)
        self.score = kwargs.get('score', 0)
        self.pseudonym_locale = kwargs.get('pseudonym_locale', 'en_US')

        # Determine the player's color.
        if 'color' in kwargs:
            self.color_idx = Gridworld.player_colors.index(kwargs['color'])
        elif 'color_name' in kwargs:
            self.color_idx = Gridworld.player_color_names.index(kwargs['color_name'])
        else:
            self.color_idx = random.randint(0, self.num_possible_colors - 1)

        self.color_name = Gridworld.player_color_names[self.color_idx]
        self.color = Gridworld.player_colors[self.color_idx]

        # Determine the player's profile.
        self.fake = Factory.create(self.pseudonym_locale)
        self.profile = self.fake.simple_profile(
            sex=kwargs.get('pseudonym_gender', None)
        )
        self.name = self.profile['name']
        self.username = self.profile['username']
        self.gender = self.profile['sex']
        self.birthdate = self.profile['birthdate']

        self.motion_timestamp = 0

    def tremble(self, direction):
        """Change direction with some probability."""
        directions = [
            "up",
            "down",
            "left",
            "right"
        ]
        directions.remove(direction)
        direction = random.choice(directions)
        return direction

    def move(self, direction, tremble_rate=0):
        """Move the player."""

        if random.random() < tremble_rate:
            direction = self.tremble(direction)

        self.motion_direction = direction

        new_position = self.position[:]

        if direction == "up":
            if self.position[0] > 0:
                new_position[0] -= 1

        elif direction == "down":
            if self.position[0] < (self.grid.rows - 1):
                new_position[0] = self.position[0] + 1

        elif direction == "left":
            if self.position[1] > 0:
                new_position[1] = self.position[1] - 1

        elif direction == "right":
            if self.position[1] < (self.grid.columns - 1):
                new_position[1] = self.position[1] + 1

        # Update motion.
        now_relative = time.time() - self.grid.start_timestamp
        wait_time = 1.0 / self.speed_limit
        can_move = now_relative > (self.motion_timestamp + wait_time)

        can_afford_to_move = self.score >= self.motion_cost

        if can_move and can_afford_to_move:
            if (self.grid.player_overlap or (
                (not self.grid._has_player(new_position)) and
                (not self.grid._has_wall(new_position))
            )):
                self.position = new_position
                self.motion_timestamp = now_relative
                self.score -= self.motion_cost

    def is_neighbor(self, player, d=1):
        """Determine whether other player is adjacent."""
        manhattan_distance = (
            abs(self.position[0] - player.position[0]) +
            abs(self.position[1] - player.position[1])
        )
        return (manhattan_distance <= d)

    def neighbors(self, d=1):
        """Return all adjacent players."""
        return [
            p for p in self.grid.players if (
                self.is_neighbor(p, d=d) and (p is not self)
            )
        ]

    def serialize(self):
        return {
            "id": self.id,
            "position": self.position,
            "score": self.score,
            "color": self.color,
            "motion_auto": self.motion_auto,
            "motion_direction": self.motion_direction,
            "speed_limit": self.speed_limit,
            "motion_timestamp": self.motion_timestamp,
            "name": self.name,
        }


def generate_maze(columns=25, rows=25):

    c = (columns - 1) / 2
    r = (rows - 1) / 2

    visited = [[0] * c + [1] for _ in range(r)] + [[1] * (c + 1)]
    ver = [["* "] * c + ['*'] for _ in range(r)] + [[]]
    hor = [["**"] * c + ['*'] for _ in range(r + 1)]

    sx = random.randrange(c)
    sy = random.randrange(r)
    visited[sy][sx] = 1
    stack = [(sx, sy)]
    while len(stack) > 0:
        (x, y) = stack.pop()
        d = [
            (x - 1, y),
            (x, y + 1),
            (x + 1, y),
            (x, y - 1)
        ]
        random.shuffle(d)
        for (xx, yy) in d:
            if visited[yy][xx]:
                continue
            if xx == x:
                hor[max(y, yy)][x] = "* "
            if yy == y:
                ver[y][max(x, xx)] = "  "
            stack.append((xx, yy))
            visited[yy][xx] = 1

    # Convert the maze to a list of wall cell positions.
    the_rows = ([j for i in zip(hor, ver) for j in i])
    the_rows = [list("".join(j)) for j in the_rows]
    maze = [item is '*' for sublist in the_rows for item in sublist]
    walls = []
    for idx in range(len(maze)):
        if maze[idx]:
            walls.append((idx / columns, idx % columns))

    return walls


def fermi(beta, p1, p2):
    """The Fermi function from statistical physics."""
    return 2.0 * ((1.0 / (1 + math.exp(-beta * (p1 - p2)))) - 0.5)


extra_routes = Blueprint(
    'extra_routes',
    __name__,
    template_folder='templates',
    static_folder='static')


@extra_routes.route('/')
def index():
    return render_template('index.html')


@extra_routes.route("/consent")
def consent():
    """Return the consent form. Here for backwards-compatibility with 2.x."""
    return render_template(
        "consent.html",
        hit_id=request.args['hit_id'],
        assignment_id=request.args['assignment_id'],
        worker_id=request.args['worker_id'],
        mode=config.get('mode'),
    )


@extra_routes.route("/grid")
def serve_grid():
    """Return the game stage."""
    return render_template("grid.html")


class Griduniverse(dallinger.experiments.Experiment):
    """Define the structure of the experiment."""

    def __init__(self, session):
        """Initialize the experiment."""
        super(Griduniverse, self).__init__(session)
        self.experiment_repeats = 1
        self.initial_recruitment_size = 1
        self.setup()
        self.clients = []

        self.grid = Gridworld(
            num_players=8,
            num_food=8,
            columns=25,
            rows=25,
            block_size=10,
            padding=1,
            num_colors=2,
            respawn_food=True,
            food_visible=True,
            food_reward=1,
            food_pg_multiplier=0,
            food_growth_rate=1.00,
            mutable_colors=True,
            costly_colors=True,
            dollars_per_point=0.02,
            initial_score=50,
            player_overlap=False,
            background_animation=True,
            time=300,
            tax=0,
            walls=None,
            walls_visible=True,
            show_grid=True,
            visibility=1000,
            speed_limit=8,
            motion_auto=False,
            motion_cost=0,
            motion_tremble_rate=0.00,
            frequency_dependence=0,
            frequency_dependent_payoff_rate=0,
            chatroom=True,
            contagion=5,
            contagion_hierarchy=True,
            donation=1,
            pseudonyms=True,
            pseudonyms_locale="it_IT",
            pseudonyms_gender=None,
            relative_deprivation=1,
        )

        # Register Socket.IO event handler.
        socketio.on_event('connect', self.handle_connect)
        socketio.on_event('disconnect', self.handle_disconnect)
        socketio.on_event('message', self.handle_message)
        socketio.on_event('change_color', self.handle_change_color)
        socketio.on_event('move', self.handle_move)
        socketio.on_event('donate', self.handle_donate)

    def setup(self):
        """Setup the networks."""
        if not self.networks():
            super(Griduniverse, self).setup()
            for net in self.networks():
                dallinger.nodes.Environment(network=net)

    def recruit(self):
        pass

    def handle_connect(self):
        print("Client {} has connected.".format(request.sid))
        client_count = len([c for c in self.clients if c is not -1])
        print("Grid num players: {}".format(self.grid.num_players))
        if client_count < self.grid.num_players:
            self.clients.append(request.sid)
            self.grid.spawn_player(id=self.clients.index(request.sid))

    def handle_disconnect(self):
        print('Client {} has disconnected.'.format(request.sid))
        self.clients[self.clients.index(request.sid)] = -1

    def handle_message(self, msg):
        socketio.emit('message', msg, broadcast=True)

    def handle_change_color(self, msg):
        player = self.grid.players[msg['player']]
        color_idx = Gridworld.player_colors.index(msg['color'])

        if player.color_idx == color_idx:
            return  # Requested color change is no change at all.

        if self.grid.costly_colors:
            if player.score < self.grid.color_costs[color_idx]:
                return
            else:
                player.score -= self.grid.color_costs[color_idx]

        player.color = msg['color']
        player.color_idx = color_idx
        player.color_name = Gridworld.player_color_names[color_idx]

    def handle_move(self, msg):
        player = self.grid.players[msg['player']]
        player.move(msg['move'], tremble_rate=player.motion_tremble_rate)

    def handle_donate(self, msg):
        """Send a donation from one player to another."""
        player_to = self.grid.players[msg['player_to']]
        player_from = self.grid.players[msg['player_from']]
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
                room=self.clients[player_to.id]
            )

    @property
    def background_tasks(self):
        return [
            self.send_state_thread,
            self.game_loop,
        ]

    def send_state_thread(self):
        """Example of how to send server-generated events to clients."""
        count = 0
        socketio.sleep(1.00)
        while True:
            socketio.sleep(0.050)
            count += 1
            socketio.emit(
                'state',
                {
                    'state_json': self.grid.serialize(),
                    'clients': self.clients,
                    'count': count,
                    'remaining_time': time.time() - self.grid.start_timestamp,
                },
                broadcast=True,
            )

    def game_loop(self):
        """Update the world state."""
        from dallinger.db import db_url
        engine = create_engine(db_url, pool_size=1000)
        session = scoped_session(
            sessionmaker(
                autocommit=False,
                autoflush=True,
                bind=engine
            )
        )

        previous_second_timestamp = self.grid.start_timestamp

        socketio.sleep(0.200)

        environment = session.query(dallinger.nodes.Environment).one()

        complete = False
        while not complete:

            state = environment.update(self.grid.serialize())
            session.add(state)
            session.commit()

            socketio.sleep(0.010)

            now = time.time()

            # Update motion.
            if self.grid.motion_auto:
                for player in self.grid.players:
                    player.move(player.motion_direction, tremble_rate=0)

            # Consume the food.
            self.grid.consume()

            # Spread through contagion.
            if self.grid.contagion > 0:
                self.grid.spread_contagion()

            # Trigger time-based events.
            if (now - previous_second_timestamp) > 1.000:

                # Grow the food stores.
                self.grid.num_food = max(min(
                    self.grid.num_food * self.grid.food_growth_rate,
                    self.grid.rows * self.grid.columns,
                ), 0)

                for i in range(int(round(self.grid.num_food) - len(self.grid.food))):
                    self.grid.spawn_food()

                for i in range(len(self.grid.food) - int(round(self.grid.num_food))):
                    self.grid.food.remove(random.choice(self.grid.food))

                for player in self.grid.players:
                    # Apply tax.
                    player.score = max(player.score - self.grid.tax, 0)

                    # Apply frequency-dependent payoff.
                    for player in self.grid.players:
                        abundance = len(
                            [p for p in self.grid.players if p.color == player.color]
                        )
                        relative_frequency = 1.0 * abundance / len(self.grid.players)
                        payoff = fermi(
                            beta=self.grid.frequency_dependence,
                            p1=relative_frequency,
                            p2=0.5
                        ) * self.grid.frequency_dependent_payoff_rate

                        player.score = max(player.score + payoff, 0)

                previous_second_timestamp = now

            # Check if the game is over.
            if (now - self.grid.start_timestamp) > self.grid.time:
                complete = True
                socketio.emit('stop', {}, broadcast=True)
