"""The Griduniverse."""

import flask
import gevent
import json
import logging
import math
import random
import time
import uuid

from cached_property import cached_property
from faker import Factory
from sqlalchemy import create_engine
from sqlalchemy.orm import (
    sessionmaker,
    scoped_session,
)

import dallinger
from dallinger.compat import unicode
from dallinger.config import get_config
from dallinger.experiment import Experiment
from dallinger.heroku.worker import conn as redis

from bots import Bot

logger = logging.getLogger(__file__)
config = get_config()

# Make bot importable without triggering style warnings
Bot = Bot


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
        'others_visible': bool,
        'num_colors': int,
        'mutable_colors': bool,
        'costly_colors': bool,
        'pseudonyms': bool,
        'pseudonyms_locale': unicode,
        'pseudonyms_gender': unicode,
        'contagion': int,
        'contagion_hierarchy': bool,
        'walls_density': float,
        'walls_contiguity': float,
        'walls_visible': bool,
        'initial_score': int,
        'dollars_per_point': float,
        'tax': float,
        'relative_deprivation': float,
        'frequency_dependence': float,
        'frequency_dependent_payoff_rate': float,
        'donation_amount': int,
        'donation_individual': bool,
        'donation_group': bool,
        'donation_public': bool,
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
        'difi_question': bool,
        'difi_group_label': unicode,
        'difi_group_image': unicode,
        'leach_survey': bool,
        'intergroup_competition': float,
        'intragroup_competition': float,
        'identity_signaling': bool,
        'identity_starts_visible': bool,
    }

    for key in types:
        config.register(key, types[key])


def softmax(vector, temperature=1):
    """The softmax activation function."""
    vector = [math.pow(x, temperature) for x in vector]
    if sum(vector):
        return [float(x) / sum(vector) for x in vector]
    else:
        return [float(len(vector)) for _ in vector]


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

    def __new__(cls, **kwargs):
        if not hasattr(cls, 'instance'):
            cls.instance = super(Gridworld, cls).__new__(cls)
        return cls.instance

    def __init__(self, **kwargs):
        # If Singleton is already initialized, do nothing
        if hasattr(self, 'num_players'):
            return

        # Players
        self.num_players = kwargs.get('max_participants', 3)

        # Rounds
        self.num_rounds = kwargs.get('num_rounds', 1)
        self.time_per_round = kwargs.get('time_per_round', 300)

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
        self.others_visible = kwargs.get('others_visible', True)
        self.num_colors = kwargs.get('num_colors', 3)
        self.mutable_colors = kwargs.get('mutable_colors', False)
        self.costly_colors = kwargs.get('costly_colors', False)
        self.pseudonyms = kwargs.get('pseudonyms', True)
        self.pseudonyms_locale = kwargs.get('pseudonyms_locale', 'en_US')
        self.pseudonyms_gender = kwargs.get('pseudonyms_gender', None)
        self.contagion = kwargs.get('contagion', 0)
        self.contagion_hierarchy = kwargs.get('contagion_hierarchy', False)
        self.identity_signaling = kwargs.get('identity_signaling', False)
        self.identity_starts_visible = kwargs.get('identity_starts_visible',
                                                  False)

        # Walls
        self.walls_visible = kwargs.get('walls_visible', True)
        self.walls_density = kwargs.get('walls_density', 0.0)
        self.walls_contiguity = kwargs.get('walls_contiguity', 1.0)

        # Payoffs
        self.initial_score = kwargs.get('initial_score', 0)
        self.dollars_per_point = kwargs.get('dollars_per_point', 0.02)
        self.tax = kwargs.get('tax', 0.01)
        self.relative_deprivation = kwargs.get('relative_deprivation', 1)
        self.frequency_dependence = kwargs.get('frequency_dependence', 0)
        self.frequency_dependent_payoff_rate = kwargs.get(
            'frequency_dependent_payoff_rate', 0)
        self.donation_amount = kwargs.get('donation_amount', 0)
        self.donation_individual = kwargs.get('donation_individual', False)
        self.donation_group = kwargs.get('donation_group', False)
        self.donation_public = kwargs.get('donation_public', False)
        self.intergroup_competition = kwargs.get('intergroup_competition', 1)
        self.intragroup_competition = kwargs.get('intragroup_competition', 1)

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

        # Questionnaire
        self.difi_question = kwargs.get('difi_question', False)
        self.difi_group_label = kwargs.get('difi_group_label', 'Group')
        self.difi_group_image = kwargs.get('difi_group_image', '/static/images/group.jpg')
        self.leach_survey = kwargs.get('leach_survey', False)

        # Set some variables.
        self.players = {}
        self.food = []
        self.food_consumed = []
        self.start_timestamp = kwargs.get('start_timestamp', None)
        labyrinth = Labyrinth(
            columns=self.columns,
            rows=self.rows,
            density=self.walls_density,
            contiguity=self.walls_contiguity,
        )
        self.walls = labyrinth.walls

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

    def can_occupy(self, position):
        if self.player_overlap:
            return not self.has_wall(position)
        return not self.has_player(position) and not self.has_wall(position)

    @property
    def elapsed_round_time(self):
        if self.start_timestamp is None:
            return 0
        return time.time() - self.start_timestamp

    @property
    def remaining_round_time(self):
        if self.start_timestamp is None:
            return 0
        raw_remaining = self.time_per_round - self.elapsed_round_time

        return max(0, raw_remaining)

    def check_round_completion(self):
        if not self.game_started:
            return

        if not self.remaining_round_time:
            self.round += 1
            if self.game_over:
                return

            self.start_timestamp = time.time()
            for player in self.players.values():
                player.motion_timestamp = 0

    def compute_payoffs(self):
        """Compute payoffs from scores.

        A player's payoff in the game can be expressed as the product of four
        factors: the grand total number of points earned by all players, the
        (softmax) proportion of the total points earned by the player's group,
        the (softmax) proportion of the group's points earned by the player,
        and the number of dollars per point.

        Softmaxing the two proportions implements intragroup and intergroup
        competition. When the parameters are 1, payoff is proportional to what
        was scored and so there is no extrinsic competition. Increasing the
        temperature introduces competition. For example, at 2, a pair of groups
        that score in a 2:1 ratio will get payoff in a 4:1 ratio, and therefore
        it pays to be in the highest-scoring group. The same logic applies to
        intragroup competition: when the temperature is 2, a pair of players
        within a group that score in a 2:1 ratio will get payoff in a 4:1
        ratio, and therefore it pays to be a group's highest-scoring member.
        """
        players = self.players.values()
        group_scores = []
        for g in range(len(self.player_colors)):
            ingroup_players = [p for p in players if p.color_idx == g]
            ingroup_scores = [p.score for p in ingroup_players]
            group_scores.append(sum(ingroup_scores))
            intra_proportions = softmax(
                ingroup_scores,
                temperature=self.intragroup_competition,
            )
            for i, player in enumerate(ingroup_players):
                player.payoff = sum([p.score for p in players])  # grand score
                player.payoff *= intra_proportions[i]

        inter_proportions = softmax(
            group_scores,
            temperature=self.intergroup_competition,
        )
        for player in players:
            player.payoff *= inter_proportions[player.color_idx]
            player.payoff *= self.dollars_per_point

    def _start_if_ready(self):
        # Don't start unless we have a least one player
        if self.players and not self.game_started:
            self.start_timestamp = time.time()

    @property
    def game_started(self):
        return self.start_timestamp is not None

    @property
    def game_over(self):
        return self.round >= self.num_rounds

    def serialize(self):
        return json.dumps({
            "players": [player.serialize() for player in self.players.values()],
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
            for player in self.players.values():
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
                    for player_to in self.players.values():
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
            identity_visible=(not self.identity_signaling or
                              self.identity_starts_visible),
        )
        self.players[id] = player
        self._start_if_ready()

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
            self.has_player(position) or
            self.has_food(position) or
            self.has_wall(position)
        )

    def has_player(self, position):
        for player in self.players.values():
            if player.position == position:
                return True
        return False

    def has_food(self, position):
        for food in self.food:
            if food.position == position:
                return True
        return False

    def has_wall(self, position):
        for wall in self.walls:
            if wall.position == position:
                return True
        return False

    def spread_contagion(self):
        """Spread contagion."""
        color_updates = []
        for player in self.players.values():
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
        self.payoff = kwargs.get('payoff', 0)
        self.pseudonym_locale = kwargs.get('pseudonym_locale', 'en_US')
        self.identity_visible = kwargs.get('identity_visible', True)

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
        elapsed_time = self.grid.elapsed_round_time
        wait_time = 1.0 / self.motion_speed_limit
        can_move = elapsed_time > (self.motion_timestamp + wait_time)
        can_afford_to_move = self.score >= self.motion_cost

        if can_move and can_afford_to_move and self.grid.can_occupy(new_position):
            self.position = new_position
            self.motion_timestamp = elapsed_time
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
            p for p in self.grid.players.values() if (
                self.is_neighbor(p, d=d) and (p is not self)
            )
        ]

    def serialize(self):
        return {
            "id": self.id,
            "position": self.position,
            "score": self.score,
            "payoff": self.payoff,
            "color": self.color,
            "motion_auto": self.motion_auto,
            "motion_direction": self.motion_direction,
            "motion_speed_limit": self.motion_speed_limit,
            "motion_timestamp": self.motion_timestamp,
            "name": self.name,
            "identity_visible": self.identity_visible,
        }


class Labyrinth(object):
    """A maze generator."""
    def __init__(self, columns=25, rows=25, density=1.0, contiguity=1.0):
        if density:
            walls = self._generate_maze(rows, columns)
            self.walls = self._prune(walls, density, contiguity)
        else:
            self.walls = []

    def _generate_maze(self, rows, columns):

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
        maze = [item == '*' for sublist in the_rows for item in sublist]
        walls = []
        for idx, value in enumerate(maze):
            if value:
                walls.append(Wall(position=[idx / columns, idx % columns]))

        return walls

    def _prune(self, walls, density, contiguity):
        """Prune walls to a labyrinth with the given density and contiguity."""
        num_to_prune = int(round(len(walls) * (1 - density)))
        num_pruned = 0
        while num_pruned < num_to_prune:
            (terminals, nonterminals) = self._classify_terminals(walls)
            walls_to_prune = terminals[:num_to_prune]
            for w in walls_to_prune:
                walls.remove(w)
            num_pruned += len(walls_to_prune)

        num_to_prune = int(round(len(walls) * (1 - contiguity)))
        for _ in range(num_to_prune):
            walls.remove(random.choice(walls))

        return walls

    def _classify_terminals(self, walls):
        terminals = []
        nonterminals = []
        positions = [w.position for w in walls]
        for w in walls:
            num_neighbors = 0
            num_neighbors += [w.position[0] + 1, w.position[1]] in positions
            num_neighbors += [w.position[0] - 1, w.position[1]] in positions
            num_neighbors += [w.position[0], w.position[1] + 1] in positions
            num_neighbors += [w.position[0], w.position[1] - 1] in positions
            if num_neighbors == 1:
                terminals.append(w)
            else:
                nonterminals.append(w)
        return (terminals, nonterminals)


def fermi(beta, p1, p2):
    """The Fermi function from statistical physics."""
    return 2.0 * ((1.0 / (1 + math.exp(-beta * (p1 - p2)))) - 0.5)


extra_routes = flask.Blueprint(
    'extra_routes',
    __name__,
    template_folder='templates',
    static_folder='static')


@extra_routes.route('/')
def index():
    return flask.render_template('index.html')


@extra_routes.route("/consent")
def consent():
    """Return the consent form. Here for backwards-compatibility with 2.x."""
    return flask.render_template(
        "consent.html",
        hit_id=flask.request.args['hit_id'],
        assignment_id=flask.request.args['assignment_id'],
        worker_id=flask.request.args['worker_id'],
        mode=config.get('mode'),
    )


@extra_routes.route("/grid")
def serve_grid():
    """Return the game stage."""
    return flask.render_template("grid.html")


class Griduniverse(Experiment):
    """Define the structure of the experiment."""
    channel = 'griduniverse_ctrl'

    def __init__(self, session=None):
        """Initialize the experiment."""
        super(Griduniverse, self).__init__(session)
        self.experiment_repeats = 1
        if session:
            self.setup()
            self.grid = Gridworld(**config.as_dict())

    def configure(self):
        super(Griduniverse, self).configure()
        self.num_participants = config.get('max_participants', 3)
        self.initial_recruitment_size = config.get('max_participants', 3)
        self.network_factory = config.get('network', 'FullyConnected')

    @property
    def environment(self):
        environment = self.session.query(dallinger.nodes.Environment).one()

        return environment

    @cached_property
    def session(self):
        from dallinger.db import db_url
        engine = create_engine(db_url, pool_size=1000)
        session = scoped_session(
            sessionmaker(autocommit=False, autoflush=True, bind=engine)
        )

        return session

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

    def bonus(self, participant):
        """The bonus to be awarded to the given participant.

        Return the value of the bonus to be paid to `participant`.
        """
        data = self._last_state_for_player(participant.id)
        if not data:
            return 0.0

        return float("{0:.2f}".format(data['payoff']))

    def bonus_reason(self):
        """The reason offered to the participant for giving the bonus.
        """
        return (
            "Thank for participating! You earned a bonus based on your "
            "performance in Griduniverse!"
        )

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
            'toggle_visible': self.handle_toggle_visible,
        }
        if msg['type'] in mapping:
            mapping[msg['type']](msg)

    def send(self, raw_message):
        """Socket interface; point of entry for incoming messages.

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
        if player_id == 'spectator':
            logger.info('A spectator has connected.')
            return

        logger.info("Client {} has connected.".format(player_id))
        client_count = len(self.grid.players)
        logger.info("Grid num players: {}".format(self.grid.num_players))
        if client_count < self.grid.num_players:
            participant = dallinger.models.Participant.query.get(player_id)
            network = self.get_network_for_participant(participant)
            if network:
                logger.info("Found an open network. Adding participant node...")
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

    def handle_donation(self, msg):
        """Send a donation from one player to another."""
        recipients = []
        recipient_id = msg['recipient_id']
        if recipient_id.startswith('group:') and self.grid.donation_group:
            group = recipient_id[6:]
            for player in self.grid.players.values():
                if (player.color_idx == int(group) and
                        player.id != msg['donor_id']):
                    recipients.append(player)
        elif recipient_id == 'all' and self.grid.donation_public:
            recipients = [p for p in self.grid.players.values()
                          if p.id != msg['donor_id']]
        else:
            if self.grid.donation_individual:
                recipient = self.grid.players.get(recipient_id)
                if recipient:
                    recipients.append(recipient)
        donor = self.grid.players[msg['donor_id']]
        donation = msg['amount']

        if donor.score >= donation and len(recipients):
            donor.score -= donation
            if len(recipients) > 1:
                donation = round(donation * 1.0 / len(recipients), 2)
            for recipient in recipients:
                recipient.score += donation
            message = {
                'type': 'donation_processed',
                'donor_id': msg['donor_id'],
                'recipient_id': msg['recipient_id'],
                'amount': donation,
            }
            self.publish(message)

    def handle_plant_food(self, msg):
        player = self.grid.players[msg['player']]
        position = msg['position']
        can_afford = player.score >= self.grid.food_planting_cost
        if (can_afford and not self.grid.has_food(position)):
            player.score -= self.grid.food_planting_cost
            self.grid.spawn_food(position=position)

    def handle_toggle_visible(self, msg):
        player = self.grid.players[msg['player']]
        player.identity_visible = msg['identity_visible']

    def send_state_thread(self):
        """Publish the current state of the grid and game"""
        count = 0
        gevent.sleep(1.00)
        while True:
            gevent.sleep(0.050)
            count += 1
            message = {
                'type': 'state',
                'grid': self.grid.serialize(),
                'count': count,
                'remaining_time': self.grid.remaining_round_time,
                'round': self.grid.round,
            }
            self.publish(message)
            if self.grid.game_over:
                return

    def game_loop(self):
        """Update the world state."""
        gevent.sleep(0.200)

        while not self.grid.game_started:
            gevent.sleep(0.01)

        previous_second_timestamp = self.grid.start_timestamp

        while not self.grid.game_over:
            # Record grid state to database
            state = self.environment.update(self.grid.serialize())
            self.session.add(state)
            self.session.commit()

            gevent.sleep(0.010)

            now = time.time()

            # Update motion.
            if self.grid.motion_auto:
                for player in self.grid.players.values():
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

                for player in self.grid.players.values():
                    # Apply tax.
                    player.score = max(player.score - self.grid.tax, 0)

                    # Apply frequency-dependent payoff.
                    for player in self.grid.players.values():
                        abundance = len(
                            [p for p in self.grid.players.values() if p.color == player.color]
                        )
                        relative_frequency = 1.0 * abundance / len(self.grid.players)
                        payoff = fermi(
                            beta=self.grid.frequency_dependence,
                            p1=relative_frequency,
                            p2=0.5
                        ) * self.grid.frequency_dependent_payoff_rate

                        player.score = max(player.score + payoff, 0)

                previous_second_timestamp = now

            self.grid.compute_payoffs()
            self.grid.check_round_completion()

        self.publish({'type': 'stop'})
        return

    def analyze(self, data):
        return self.average_score(data)

    def average_score(self, data):
        final_state = json.loads(data.infos.list[-1][-1])
        players = final_state['players']
        scores = [player['score'] for player in players]
        return float(sum(scores)) / len(scores)

    def _last_state_for_player(self, player_id):
        most_recent_grid_state = self.environment.state()
        players = json.loads(most_recent_grid_state.contents)['players']
        id_matches = [p for p in players if int(p['id']) == player_id]
        if id_matches:
            return id_matches[0]