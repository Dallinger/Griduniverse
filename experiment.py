"""The Griduniverse."""

import json
import logging
import math
import random
import time
import uuid

import gevent
from faker import Factory
from flask import (
    Blueprint,
    render_template,
    request,
)
from sqlalchemy import create_engine
from sqlalchemy.orm import (
    sessionmaker,
    scoped_session,
)

import dallinger
from dallinger.heroku.worker import conn as redis
from dallinger.compat import unicode
from dallinger.config import get_config
from dallinger.experiments import Experiment

logger = logging.getLogger(__file__)
config = get_config()


def extra_parameters():

    types = {
        'network': unicode,
        'max_participants': int,
        'bot_policy': unicode,
        'num_rounds': int,
        'time_per_round': float,
        'instruct': bool,
        'columns': int,
        'rows': int,
        'block_size': int,
        'padding': int,
        'visibility': int,
        'background_animation': bool,
        'player_overlap': bool,
        'motion_speed_limit': float,
        'motion_auto': bool,
        'motion_cost': float,
        'motion_tremble_rate': float,
        'show_chatroom': bool,
        'show_grid': bool,
        'num_colors': int,
        'mutable_colors': bool,
        'costly_colors': bool,
        'pseudonyms': bool,
        'pseudonyms_locale': unicode,
        'pseudonyms_gender': unicode,
        'contagion': int,
        'contagion_hierarchy': bool,
        'walls': unicode,
        'walls_visible': bool,
        'initial_score': int,
        'dollars_per_point': float,
        'tax': float,
        'relative_deprivation': float,
        'frequency_dependence': float,
        'frequency_dependent_payoff_rate': float,
        'donation': int,
        'num_food': int,
        'respawn_food': bool,
        'food_visible': bool,
        'food_reward': int,
        'food_pg_multiplier': float,
        'food_growth_rate': float,
        'food_maturation_speed': float,
        'food_maturation_threshold': float,
        'food_planting': bool,
        'food_planting_cost': int,
        'seasonal_growth_rate': float,
    }

    for key in types:
        config.register(key, types[key])


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

        # Players
        self.num_players = kwargs.get('max_participants', 3)

        # Rounds
        self.num_rounds = kwargs.get('num_rounds', 1)
        self.time_per_round = kwargs.get('time_per_round', 30)

        # Instructions
        self.instruct = kwargs.get('instruct', True)

        # Grid
        self.columns = kwargs.get('columns', 25)
        self.rows = kwargs.get('rows', 25)
        self.block_size = kwargs.get('block_size', 10)
        self.padding = kwargs.get('padding', 1)
        self.visibility = kwargs.get('visibility', 1000)
        self.background_animation = kwargs.get('background_animation', True)
        self.player_overlap = kwargs.get('player_overlap', False)

        # Motion
        self.motion_speed_limit = kwargs.get('motion_speed_limit', 16)
        self.motion_auto = kwargs.get('motion_auto', False)
        self.motion_cost = kwargs.get('motion_cost', 0)
        self.motion_tremble_rate = kwargs.get('motion_tremble_rate', 0)

        # Components
        self.show_chatroom = kwargs.get('show_chatroom', True)
        self.show_grid = kwargs.get('show_grid', True)

        # Identity
        self.num_colors = kwargs.get('num_colors', 3)
        self.mutable_colors = kwargs.get('mutable_colors', False)
        self.costly_colors = kwargs.get('costly_colors', False)
        self.pseudonyms = kwargs.get('pseudonyms', True)
        self.pseudonyms_locale = kwargs.get('pseudonyms_locale', 'en_US')
        self.pseudonyms_gender = kwargs.get('pseudonyms_gender', None)
        self.contagion = kwargs.get('contagion', 0)
        self.contagion_hierarchy = kwargs.get('contagion_hierarchy', False)

        # Walls
        self.wall_type = kwargs.get('walls', None)
        self.walls_visible = kwargs.get('walls_visible', True)

        # Payoffs
        self.initial_score = kwargs.get('initial_score', 0)
        self.dollars_per_point = kwargs.get('dollars_per_point', 0.02)
        self.tax = kwargs.get('tax', 0.01)
        self.relative_deprivation = kwargs.get('relative_deprivation', 1)
        self.frequency_dependence = kwargs.get('frequency_dependence', 0)
        self.frequency_dependent_payoff_rate = kwargs.get(
            'frequency_dependent_payoff_rate', 0)
        self.donation = kwargs.get('donation', 0)

        # Food
        self.num_food = kwargs.get('num_food', 8)
        self.respawn_food = kwargs.get('respawn_food', True)
        self.food_visible = kwargs.get('food_visible', True)
        self.food_reward = kwargs.get('food_reward', 1)
        self.food_pg_multiplier = kwargs.get('food_pg_multiplier', 1)
        self.food_growth_rate = kwargs.get('food_growth_rate', 1.00)
        self.food_maturation_speed = kwargs.get('food_maturation_speed', 1)
        self.food_maturation_threshold = kwargs.get(
            'food_maturation_threshold', 0.0)
        self.food_planting = kwargs.get('food_planting', False)
        self.food_planting_cost = kwargs.get('food_planting_cost', 1)
        self.seasonal_growth_rate = kwargs.get('seasonal_growth_rate', 1)

        # Set some variables.
        self.players = []
        self.food = []
        self.food_consumed = []
        self.start_timestamp = kwargs.get('start_timestamp', time.time())
        self.walls = self.generate_walls(style=self.wall_type)
        self.round = 0
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
            "round": self.round,
            "rows": self.rows,
            "columns": self.columns,
        })

    @property
    def food_mature(self):
        return [f for f in self.food
                if f.maturity >= self.food_maturation_threshold]

    def consume(self):
        """Players consume the food."""
        for food in self.food_mature:
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

    def spawn_food(self, position=None):
        """Respawn the food."""
        if not position:
            position = self._random_empty_position()

        self.food.append(Food(
            id=(len(self.food) + len(self.food_consumed)),
            position=position,
            maturation_speed=self.food_maturation_speed,
        ))

    def spawn_player(self, id=None):
        """Spawn a player."""
        player = Player(
            id=id,
            position=self._random_empty_position(),
            num_possible_colors=self.num_colors,
            motion_speed_limit=self.motion_speed_limit,
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

    def get_player(self, id):
        """Get a player by ID"""
        for player in self.players:
            if player.id == id:
                return player

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
        self.maturation_speed = kwargs.get('maturation_speed', 0.1)
        self.creation_timestamp = time.time()

    def serialize(self):
        return {
            "id": self.id,
            "position": self.position,
            "maturity": self.maturity,
            "color": self._maturity_to_rgb(self.maturity),
        }

    def _maturity_to_rgb(self, maturity):
        B = [0.48, 0.42, 0.33]  # Brown
        G = [0.54, 0.61, 0.06]  # Green
        return [B[i] + maturity * (G[i] - B[i]) for i in range(3)]

    @property
    def maturity(self):
        return 1 - math.exp(-self._age * self.maturation_speed)

    @property
    def _age(self):
        return time.time() - self.creation_timestamp


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
        self.motion_speed_limit = kwargs.get('motion_speed_limit', 8)
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
        wait_time = 1.0 / self.motion_speed_limit
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
            "motion_speed_limit": self.motion_speed_limit,
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


class Griduniverse(Experiment):
    """Define the structure of the experiment."""
    channel = 'griduniverse_ctrl'

    def __init__(self, session=None):
        """Initialize the experiment."""
        super(Griduniverse, self).__init__(session)
        self.experiment_repeats = 1
        self.num_participants = config.get('max_participants', 3)
        self.initial_recruitment_size = config.get('max_participants', 3)
        self.network_factory = config.get('network', 'FullyConnected')
        if session:
            self.setup()

        self.grid = Gridworld(**config.as_dict())

    @property
    def background_tasks(self):
        return [
            self.send_state_thread,
            self.game_loop,
        ]

    def create_network(self):
        """Create a new network by reading the configuration file."""
        class_ = getattr(
            dallinger.networks,
            self.network_factory
        )
        return class_(max_size=self.num_participants + 1)

    def setup(self):
        """Setup the networks."""
        if not self.networks():
            super(Griduniverse, self).setup()
            for net in self.networks():
                dallinger.nodes.Environment(network=net)

    def recruit(self):
        self.recruiter().close_recruitment()

    def dispatch(self, msg):
        """Route to the appropriate method based on message type"""
        mapping = {
            'connect': self.handle_connect,
            'disconnect': self.handle_disconnect,
            'message': self.handle_chat_message,
            'change_color': self.handle_change_color,
            'move': self.handle_move,
            'donation_submitted': self.handle_donation,
            'plant_food': self.handle_plant_food,
        }
        if msg['type'] in mapping:
            mapping[msg['type']](msg)

    def send(self, raw_message):
        """socket interface implementation, and point of entry for incoming
        messages.

        param raw_message is a string with a channel prefix, for example:

            'griduniverse:{"type":"move","player":0,"move":"left"}'
        """
        if raw_message.startswith(self.channel + ":"):
            logger.info("We received a message for our channel: {}".format(
                raw_message))
            body = raw_message.replace(self.channel + ":", "")
            message = json.loads(body)
            self.dispatch((message))
        else:
            logger.info("Received a message, but not our channel: {}".format(
                raw_message))

    def publish(self, msg):
        """Publish a message to all griduniverse clients"""
        redis.publish('griduniverse', json.dumps(msg))

    def handle_connect(self, msg):
        player_id = msg['player_id']
        logger.info("Client {} has connected.".format(player_id))
        client_count = len(self.grid.players)
        logger.info("Grid num players: {}".format(self.grid.num_players))
        if client_count < self.grid.num_players:
            participant = dallinger.models.Participant.query.get(player_id)
            network = self.get_network_for_participant(participant)
            if network:
                logger.info("Found on open network. Adding participant node...")
                self.create_node(participant, network)
                logger.info("Spawning player on the grid...")
                self.grid.spawn_player(id=player_id)
            else:
                logger.info(
                    "No free network found for player {}".format(player_id)
                )

    def handle_disconnect(self, msg):
        logger.info('Client {} has disconnected.'.format(msg['player_id']))

    def handle_chat_message(self, msg):
        """Publish the given message to all clients."""
        message = {
            'type': 'chat',
            'message': msg,
        }
        self.publish(message)

    def handle_change_color(self, msg):
        player = self.grid.get_player(msg['player'])
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
        player = self.grid.get_player(msg['player'])
        player.move(msg['move'], tremble_rate=player.motion_tremble_rate)

    def handle_donation(self, msg):
        """Send a donation from one player to another."""
        recipient = self.grid.get_player(msg['recipient_id'])
        donor = self.grid.get_player(msg['donor_id'])
        donation = msg['amount']

        if donor.score >= donation:
            donor.score -= donation
            recipient.score += donation
            message = {
                'type': 'donation_processed',
                'donor_id': msg['donor_id'],
                'recipient_id': msg['recipient_id'],
                'amount': donation,
            }
            self.publish(message)

    def handle_plant_food(self, msg):
        player = self.grid.get_player(msg['player'])
        position = msg['position']
        can_afford = player.score >= self.grid.food_planting_cost
        if (can_afford and not self.grid._has_food(position)):
            player.score -= self.grid.food_planting_cost
            self.grid.spawn_food(position=position)

    def send_state_thread(self):
        """Publish the current state of the grid and game"""
        count = 0
        gevent.sleep(1.00)
        while True:
            gevent.sleep(0.050)
            count += 1
            elapsed_time = time.time() - self.grid.start_timestamp
            message = {
                'type': 'state',
                'grid': self.grid.serialize(),
                'count': count,
                'remaining_time': self.grid.time_per_round - elapsed_time,
                "round": self.grid.round,
            }
            self.publish(message)
            if (self.grid.round == self.grid.num_rounds):
                return

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

        gevent.sleep(0.200)

        environment = session.query(dallinger.nodes.Environment).one()

        complete = False
        while not complete:

            state = environment.update(self.grid.serialize())
            session.add(state)
            session.commit()

            gevent.sleep(0.010)

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

                # Grow or shrink the food stores.
                seasonal_growth = (
                    self.grid.seasonal_growth_rate **
                    (-1 if self.grid.round % 2 else 1)
                )

                self.grid.num_food = max(min(
                    self.grid.num_food *
                    self.grid.food_growth_rate *
                    seasonal_growth,
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

            # Check if the round is over.
            if (now - self.grid.start_timestamp) > self.grid.time_per_round:
                self.grid.round += 1
                self.grid.start_timestamp = time.time()
                for player in self.grid.players:
                    player.motion_timestamp = 0

            if self.grid.round == self.grid.num_rounds:
                complete = True
                self.publish({'type': 'stop'})
                return

    def analyze(self, data):
        return self.average_score(data)

    def average_score(self, data):
        final_state = json.loads(data.infos.list[-1][-1])
        players = final_state['players']
        scores = [player['score'] for player in players]
        return float(sum(scores)) / len(scores)


### Bots ###
import itertools
import operator
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException
from selenium.common.exceptions import WebDriverException

from dallinger.bots import BotBase


class BaseGridUniverseBot(BotBase):

    def wait_for_grid(self):
        return WebDriverWait(self.driver, 15).until(
            EC.presence_of_element_located((By.ID, "grid"))
        )

    def get_js_variable(self, variable_name):
        try:
            script = 'return window.{};'.format(variable_name)
            result = self.driver.execute_script(script)
            if result is None:
                # In some cases (older remote Firefox)
                # we need to use window.wrappedJSObject
                script = 'return window.wrappedJSObject.{};'.format(variable_name)
                result = self.driver.execute_script(script)
        except WebDriverException:
            result = None

        if result is not None:
            return json.loads(result)

    def observe_state(self):
        return self.get_js_variable("state")

    def get_player_index(self):
        idx = self.get_js_variable("ego")
        if idx:
            return int(idx) - 1
        else:
            return None

    @property
    def food_positions(self):
        try:
            return [tuple(item['position']) for item in self.state['food']
                    if item['maturity'] > 0.5]
        except (AttributeError, TypeError):
            return []

    @property
    def player_positions(self):
        try:
            return [tuple(player['position']) for player in self.state['players']]
        except (AttributeError, TypeError):
            return []

    @property
    def my_position(self):
        if self.player_positions:
            return self.player_positions[self.player_index]
        else:
            return None


class RandomBot(BaseGridUniverseBot):
    """A bot that plays griduniverse randomly"""

    VALID_KEYS = [
        Keys.UP,
        Keys.DOWN,
        Keys.RIGHT,
        Keys.LEFT,
        Keys.SPACE,
        'r',
        'b',
        'y'
    ]

    KEY_INTERVAL = 0.1

    def get_next_key(self):
        return random.choice(self.VALID_KEYS)

    def get_wait_time(self):
        return random.expovariate(1.0 / self.KEY_INTERVAL)

    def participate(self):
        """Participate by randomly hitting valid keys"""
        grid = self.wait_for_grid()
        try:
            while True:
                time.sleep(self.get_wait_time())
                grid.send_keys(self.get_next_key())
        except StaleElementReferenceException:
            pass
        return True


class AdvantageSeekingBot(BaseGridUniverseBot):
    """A bot that plays griduniverse by going towards the food it has the
    biggest advantage over the other players at getting"""

    KEY_INTERVAL = 0.1

    def get_logical_targets(self):
        """When run on a page view that has data extracted from the grid state
        find the best targets for each of the players, where the best target
        is the closest item of food, excluding all food items that are the best
        target for another player. When the same item of food is the closest
        target for multiple players the closest player would get there first,
        so it is excluded as the best target for other players.

        For example:
        Player 1 is 3 spaces from food item 1 and 5 from food item 2.
        Player 2 is 4 spaces from food item 1 and 6 from food item 2.

        The logical targets are:
        Player 1: food item 1
        Player 2: food item 2
        """
        best_choices = {}
        # Create a mapping of (player_id, food_id) tuple to the distance between
        # the relevant player and food item
        for player, food_info in self.distances().items():
            for food_id, distance in food_info.items():
                best_choices[player, food_id] = distance
        # Sort that list based on the distance, so the closest players/food
        # pairs are first, then discard the distance
        get_key = operator.itemgetter(0)
        get_food_distance = operator.itemgetter(1)
        best_choices = sorted(best_choices.items(), key=get_food_distance)
        best_choices = map(get_key, best_choices)
        # We need to find the optimum solution, so we iterate through the
        # sorted list, discarding pairings that are inferior to previous
        # options. We keep track of player and food ids, once either has been
        # used we know that player or food item has a better choice.
        seen_players = set()
        seen_food = set()
        choices = {}
        for (player_id, food_id) in best_choices:
            if player_id in seen_players:
                continue
            if food_id in seen_food:
                continue
            seen_players.add(player_id)
            seen_food.add(food_id)
            choices[player_id] = food_id
        return choices

    def get_player_spread(self, positions=None):
        """When run after populating state data, this returns the mean
        distance between all players on the board, to be used as a heuristic
        for 'spreading out' if there are no logical targets."""
        # Allow passing positions in, to calculate the spread of a hypothetical
        # future state, rather than the current state
        if positions is None:
            positions = self.player_positions
        # Find the distances between all pairs of players
        pairs = itertools.combinations(positions, 2)
        distances = itertools.starmap(self.manhattan_distance, pairs)
        # Calculate and return the mean. distances is an iterator, so we convert
        # it to a tuple so we can more easily do sums on its data
        distances = tuple(distances)
        if distances:
            return float(sum(distances)) / len(distances)
        else:
            # There is only one player, so there are no distances between
            # players.
            return 0

    def get_expected_position(self, key):
        """Given the current state of players, if we were to push the key
        specified as a parameter, what would we expect the state to become,
        ignoring modeling of other players' behavior"""
        positions = self.player_positions
        my_position = positions[self.player_index]
        pad = 5
        rows = self.state['rows']
        if key == Keys.UP and my_position[0] > pad:
            my_position = (my_position[0]-1, my_position[1])
        if key == Keys.DOWN and my_position[0] < (rows - pad):
            my_position = (my_position[0]+1, my_position[1])
        if key == Keys.LEFT and my_position[1] > pad:
            my_position = (my_position[0], my_position[1]-1)
        if key == Keys.RIGHT and my_position[1] < (rows - pad):
            my_position = (my_position[0], my_position[1]+1)
        positions[self.player_index] = my_position
        return positions

    def get_next_key(self):
        valid_keys = []
        my_position = self.my_position
        try:
            # If there is a most logical target, we move towards it
            target_id = self.get_logical_targets()[self.player_index]
            food_position = self.food_positions[target_id]
        except KeyError:
            # Otherwise, move in a direction that increases average spread.
            current_spread = self.get_player_spread()
            for key in (Keys.UP, Keys.DOWN, Keys.LEFT, Keys.RIGHT):
                expected = self.get_expected_position(key)
                if self.get_player_spread(expected) > current_spread:
                    valid_keys.append(key)
        else:
            if food_position[0] < my_position[0]:
                valid_keys.append(Keys.UP)
            elif food_position[0] > my_position[0]:
                valid_keys.append(Keys.DOWN)
            if food_position[1] < my_position[1]:
                valid_keys.append(Keys.LEFT)
            elif food_position[1] > my_position[1]:
                valid_keys.append(Keys.RIGHT)
        if not valid_keys:
            # If there are no food items available and no movement would
            # cause the average spread of players to increase, fall back to
            # the behavior of the RandomBot
            valid_keys = RandomBot.VALID_KEYS
        return random.choice(valid_keys)

    def get_wait_time(self):
        return random.expovariate(1.0 / self.KEY_INTERVAL)

    @staticmethod
    def manhattan_distance(coord1, coord2):
        x = coord1[0] - coord2[0]
        y = coord1[1] - coord2[1]
        return abs(x) + abs(y)

    def distances(self):
        """Returns a dictionary keyed on player_id, with the value being another
        dictionary which maps the index of a food item in the positions list
        to the distance between that player and that food item."""
        distances = {}
        for i, player in enumerate(self.player_positions):
            player_distances = {}
            for j, food in enumerate(self.food_positions):
                player_distances[j] = self.manhattan_distance(player, food)
            distances[i] = player_distances
        return distances

    def participate(self):
        """Wait a random amount of time, then send a key according to
        the algorithm above."""
        grid = self.wait_for_grid()

        # Wait for state to be available
        self.state = None
        self.player_index = None
        while (self.state is None) or (self.player_index is None):
            time.sleep(0.500)
            self.state = self.observe_state()
            self.player_index = self.get_player_index()

        while True:
            time.sleep(self.get_wait_time())
            try:
                observed_state = self.observe_state()
                if observed_state:
                    self.state = observed_state
                    # This is a roundabout way of sending the key
                    # to the grid element; it's needed to avoid a
                    # "cannot focus element" error with chromedriver
                    if config.get('webdriver_type') == "chrome":
                        action = ActionChains(self.driver).move_to_element(grid)
                        action.click().send_keys(self.get_next_key()).perform()
                    else:
                        grid.send_keys(self.get_next_key())
            except (StaleElementReferenceException, AttributeError):
                return True

    def complete_questionnaire(self):
        """Complete the standard debriefing form."""
        pass


def Bot(*args, **kwargs):
    """Pick any bot implementation in this class based on a configuration
    parameter.

    This can be set in config.txt in this directory, or by environment variable.
    """

    bot_implementation = config.get('bot_policy', u'RandomBot')
    bot_class = globals().get(bot_implementation, None)
    if bot_class and issubclass(bot_class, BotBase):
        return bot_class(*args, **kwargs)
    else:
        raise NotImplementedError
