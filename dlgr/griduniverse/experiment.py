"""The Griduniverse."""

import flask
import gevent
import json
import logging
import math
import random
import string
import time
import uuid

from cached_property import cached_property
from faker import Factory
from sqlalchemy import create_engine
from sqlalchemy import and_, or_
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
from models import Event

logger = logging.getLogger(__file__)
config = get_config()

# Make bot importable without triggering style warnings
Bot = Bot


class PluralFormatter(string.Formatter):
    def format_field(self, value, format_spec):
        if format_spec.startswith('plural'):
            words = format_spec.split(',')
            if value == 1 or value == '1' or value == 1.0:
                return words[1]
            else:
                return words[2]
        else:
            return super(PluralFormatter, self).format_field(value, format_spec)


formatter = PluralFormatter()


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
        'window_columns': int,
        'window_rows': int,
        'block_size': int,
        'padding': int,
        'visibility': int,
        'visibility_ramp_time': int,
        'background_animation': bool,
        'player_overlap': bool,
        'leaderboard_group': bool,
        'leaderboard_individual': bool,
        'leaderboard_time': int,
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
        'fun_survey': bool,
        'leach_survey': bool,
        'intergroup_competition': float,
        'intragroup_competition': float,
        'identity_signaling': bool,
        'identity_starts_visible': bool,
        'score_visible': bool,
        'use_identicons': bool,
        'build_walls': bool,
        'wall_building_cost': int,
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

        self.log_event = kwargs.get('log_event', lambda x: None)

        # Players
        self.num_players = kwargs.get('max_participants', 3)

        # Rounds
        self.num_rounds = kwargs.get('num_rounds', 1)
        self.time_per_round = kwargs.get('time_per_round', 300)

        # Instructions
        self.instruct = kwargs.get('instruct', True)

        # Components
        self.show_chatroom = kwargs.get('show_chatroom', True)

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
        self.use_identicons = kwargs.get('use_identicons', False)

        # Payoffs
        self.initial_score = kwargs.get('initial_score', 0)
        self.dollars_per_point = kwargs.get('dollars_per_point', 0.02)
        self.tax = kwargs.get('tax', 0.00)
        self.relative_deprivation = kwargs.get('relative_deprivation', 1)
        self.frequency_dependence = kwargs.get('frequency_dependence', 0)
        self.frequency_dependent_payoff_rate = kwargs.get(
            'frequency_dependent_payoff_rate', 0)
        self.intergroup_competition = kwargs.get('intergroup_competition', 1)
        self.leaderboard_group = kwargs.get('leaderboard_group', False)
        self.leaderboard_individual = kwargs.get('leaderboard_individual', False)
        self.leaderboard_time = kwargs.get('leaderboard_time', 0)

        # Competition
        self.intergroup_competition = kwargs.get('intergroup_competition', 1)
        self.intragroup_competition = kwargs.get('intragroup_competition', 1)
        self.score_visible = kwargs.get('score_visible', False)

        # Questionnaire
        self.difi_question = kwargs.get('difi_question', False)
        self.difi_group_label = kwargs.get('difi_group_label', 'Group')
        self.difi_group_image = kwargs.get('difi_group_image', '/static/images/group.jpg')
        self.fun_survey = kwargs.get('fun_survey', False)
        self.leach_survey = kwargs.get('leach_survey', False)

        # Set some variables.
        self.players = {}
        self.start_timestamp = kwargs.get('start_timestamp', None)

        self.round = 0
        if self.costly_colors:
            self.color_costs = [2**i for i in range(self.num_colors)]
            random.shuffle(self.color_costs)


    @property
    def limited_player_colors(self):
        return self.player_colors[:self.num_colors]

    @property
    def limited_player_color_names(self):
        return self.player_color_names[:self.num_colors]

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

    @property
    def is_even_round(self):
        return bool(self.round % 2)

    def players_with_color(self, color_id):
        """Return all the players with the specified color, which is how we
        represent group/team membership.
        """
        color_id = int(color_id)
        return [p for p in self.players.values() if p.color_idx == color_id]

    def check_round_completion(self):
        if not self.game_started:
            return

        if not self.remaining_round_time:
            self.round += 1
            if self.game_over:
                return

            self.start_timestamp = time.time()
            # Delay round for leaderboard display
            if self.leaderboard_individual or self.leaderboard_group:
                self.start_timestamp += self.leaderboard_time
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
            "round": self.round,
        })

    def instructions(self):
        color_costs = ''
        order = ''
        text = """<p>The objective of the game is to talk"""
        if self.show_chatroom:
            text += """<p>A chatroom is available to send messages to the other
                players."""
            if self.pseudonyms:
                text += """ Player names shown on the chat window are pseudonyms.
                        <br><img src='static/images/chatroom.gif' height='150'>"""
            text += "</p>"
        if self.dollars_per_point > 0:
            text += """<p>You will receive <strong>${g.dollars_per_point}</strong> for each point
                that you score at the end of the game.</p>"""
        return formatter.format(text,
                                g=self,
                                order=order,
                                color_costs=color_costs,
                                color_list=', '.join(self.limited_player_color_names))


    def spawn_player(self, id=None, **kwargs):
        """Spawn a player."""
        player = Player(
            id=id,
            num_possible_colors=self.num_colors,
            score=self.initial_score,
            pseudonym_locale=self.pseudonyms_locale,
            pseudonym_gender=self.pseudonyms_gender,
            grid=self,
            identity_visible=(not self.identity_signaling or
                              self.identity_starts_visible),
            **kwargs
        )
        self.players[id] = player
        self._start_if_ready()
        return player


    def _empty(self, position):
        """Determine whether a particular cell is empty."""
        return not (
            self.has_player(position)
        )

    def has_player(self, position):
        for player in self.players.values():
            if player.position == position:
                return True
        return False




class Player(object):
    """A player."""

    def __init__(self, **kwargs):
        super(Player, self).__init__()

        self.id = kwargs.get('id', uuid.uuid4())
        self.num_possible_colors = kwargs.get('num_possible_colors', 2)
        self.score = kwargs.get('score', 0)
        self.payoff = kwargs.get('payoff', 0)
        self.pseudonym_locale = kwargs.get('pseudonym_locale', 'en_US')
        self.identity_visible = kwargs.get('identity_visible', True)
        self.add_wall = None

        # Determine the player's color. We don't have access to the specific
        # gridworld we are running in, so we can't use the `limited_` variables
        # We just find the index in the master list. This means it is possible
        # to explicitly instantiate a player with an invalid colour, but only
        # intentionally.
        if 'color' in kwargs:
            self.color_idx = Gridworld.player_colors.index(kwargs['color'])
        elif 'color_name' in kwargs:
            self.color_idx = Gridworld.player_color_names.index(kwargs['color_name'])
        else:
            self.color_idx = random.randint(0, self.num_possible_colors - 1)

        self.color_name = Gridworld.player_color_names[self.color_idx]
        self.color = Gridworld.player_color_names[self.color_idx]

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


    def serialize(self):
        return {
            "id": self.id,
            "score": self.score,
            "payoff": self.payoff,
            "name": self.name,
            "identity_visible": self.identity_visible,
        }


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


class Griduniverse(Experiment):
    """Define the structure of the experiment."""
    channel = 'griduniverse_ctrl'
    state_count = 0
    replay_path = '/grid'

    def __init__(self, session=None):
        """Initialize the experiment."""
        super(Griduniverse, self).__init__(session)
        self.experiment_repeats = 1
        if session:
            self.setup()
            self.grid = Gridworld(
                log_event=self.record_event,
                **config.as_dict()
            )
            self.session.commit()

    def configure(self):
        super(Griduniverse, self).configure()
        self.num_participants = config.get('max_participants', 3)
        self.quorum = self.num_participants
        self.initial_recruitment_size = config.get('max_participants', 3)
        self.network_factory = config.get('network', 'FullyConnected')

    @property
    def environment(self):
        environment = self.socket_session.query(dallinger.nodes.Environment).one()
        return environment

    @cached_property
    def socket_session(self):
        from dallinger.db import db_url
        engine = create_engine(db_url, pool_size=1000)
        session = scoped_session(
            sessionmaker(autocommit=False, autoflush=True, bind=engine)
        )
        return session

    @property
    def background_tasks(self):
        if config.get('replay', False):
            return []
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

    def create_node(self, participant, network):
        try:
            return dallinger.models.Node(
                network=network, participant=participant
            )
        finally:
            if not self.networks(full=False):
                # If there are no spaces left in our networks we can close
                # recruitment, to alleviate problems of over-recruitment
                self.recruiter().close_recruitment()

    def setup(self):
        """Setup the networks."""
        self.node_by_player_id = {}
        if not self.networks():
            super(Griduniverse, self).setup()
            for net in self.networks():
                env = dallinger.nodes.Environment(network=net)
                self.session.add(env)
        self.session.commit()

    def serialize(self, value):
        return json.dumps(value)

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
        }
        if not config.get('replay', False):
            # Ignore these events in replay mode
            mapping.update({
                'chat': self.handle_chat_message,
            })

        if msg['type'] in mapping:
            mapping[msg['type']](msg)

    def send(self, raw_message):
        """Socket interface; point of entry for incoming messages.

        param raw_message is a string with a channel prefix, for example:

            'griduniverse_ctrl:{"type":"move","player_id":0,"move":"left"}'
        """
        if raw_message.startswith(self.channel + ":"):
            logger.info("We received a message for our channel: {}".format(
                raw_message))
            body = raw_message.replace(self.channel + ":", "")
            message = json.loads(body)
            self.dispatch((message))
            if 'player_id' in message:
                self.record_event(message, message['player_id'])
        else:
            logger.info("Received a message, but not our channel: {}".format(
                raw_message))

    def record_event(self, details, player_id=None):
        """Record an event in the Info table."""
        session = self.socket_session

        if player_id == 'spectator':
            return
        elif player_id:
            node_id = self.node_by_player_id[player_id]
            node = session.query(dallinger.models.Node).get(node_id)
        else:
            node = self.environment

        info = Event(origin=node, details=details)
        session.add(info)
        session.commit()

    def publish(self, msg):
        """Publish a message to all griduniverse clients"""
        redis.publish('griduniverse', json.dumps(msg))

    def handle_connect(self, msg):
        player_id = msg['player_id']
        if config.get('replay', False):
            # Force all participants to be specatators
            msg['player_id'] = 'spectator'
            if not self.grid.start_timestamp:
                self.grid.start_timestamp = time.time()
        if player_id == 'spectator':
            logger.info('A spectator has connected.')
            return

        logger.info("Client {} has connected.".format(player_id))
        client_count = len(self.grid.players)
        logger.info("Grid num players: {}".format(self.grid.num_players))
        if client_count < self.grid.num_players:
            participant = self.session.query(dallinger.models.Participant).get(player_id)
            network = self.get_network_for_participant(participant)
            if network:
                logger.info("Found an open network. Adding participant node...")
                node = self.create_node(participant, network)
                self.node_by_player_id[player_id] = node.id
                self.session.add(node)
                self.session.commit()
                logger.info("Spawning player on the grid...")
                # We use the current node id modulo the number of colours
                # to pick the user's colour. This ensures that players are
                # allocated to colours uniformly.
                self.grid.spawn_player(
                    id=player_id,
                    color_name=self.grid.limited_player_color_names[node.id % self.grid.num_colors]
                )
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
        # We only publish if it wasn't already broadcast
        if not msg.get('broadcast', False):
            self.publish(message)

        if player.color_idx == color_idx:
            return  # Requested color change is no change at all.

        if self.grid.costly_colors:
            if player.score < self.grid.color_costs[color_idx]:
                return
            else:
                player.score -= self.grid.color_costs[color_idx]

        player.color = msg['color']
        player.color_idx = color_idx
        player.color_name = color_name
        message = {
            'type': 'color_changed',
            'player_id': msg['player_id'],
            'old_color': old_color,
            'new_color': player.color_name,
        }
        # Put the message back on the channel
        self.publish(message)
        self.record_event(message, message['player_id'])

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
            self.socket_session.add(state)
            self.socket_session.commit()

            gevent.sleep(0.010)

            now = time.time()

            game_round = self.grid.round
            self.grid.check_round_completion()
            if self.grid.round != game_round and not self.grid.game_over:
                self.publish({'type': 'new_round', 'round': self.grid.round})
                self.record_event({
                    'type': 'new_round',
                    'round': self.grid.round
                })

        self.publish({'type': 'stop'})
        self.socket_session.commit()
        return

    def player_feedback(self, data):
        engagement = int(json.loads(data.questions.list[-1][-1])['engagement'])
        difficulty = int(json.loads(data.questions.list[-1][-1])['difficulty'])
        try:
            fun = int(json.loads(data.questions.list[-1][-1])['fun'])
            return engagement, difficulty, fun
        except IndexError:
            return engagement, difficulty

    def replay_started(self):
        return self.grid.game_started

    def events_for_replay(self):
        info_cls = dallinger.models.Info
        from models import Event
        events = Experiment.events_for_replay(self)
        event_types = {'chat', 'new_round', 'color_changed'}
        return events.filter(
            or_(info_cls.type == 'state',
                and_(info_cls.type == 'event',
                     or_(*[Event.details['type'].astext == t for t in event_types]))
                )
        )

    def replay_event(self, event):
        if event.type == 'event':
            self.publish(event.details)
            if event.details.get('type') == 'new_round':
                self.grid.check_round_completion()

        if event.type == 'state':
            self.state_count += 1
            state = json.loads(event.contents)
            msg = {
                'type': 'state',
                'grid': event.contents,
                'count': self.state_count,
                'remaining_time': self.grid.remaining_round_time,
                'round': state['round'],
            }
            self.publish(msg)

    def replay_finish(self):
        self.publish({'type': 'stop'})

    def analyze(self, data):
        return json.dumps({
            "average_payoff": self.average_payoff(data),
            "average_score": self.average_score(data),
        })

    def average_payoff(self, data):
        df = data.infos.df
        dataState = df.loc[df['type'] == 'state']
        if dataState.empty:
            return 0.0
        final_state = json.loads(dataState.iloc[-1][-1])
        players = final_state['players']
        payoff = [player['payoff'] for player in players]
        return float(sum(payoff)) / len(payoff)

    def average_score(self, data):
        df = data.infos.df
        dataState = df.loc[df['type'] == 'state']
        if dataState.empty:
            return 0.0
        final_state = json.loads(dataState.iloc[-1][-1])
        players = final_state['players']
        scores = [player['score'] for player in players]
        return float(sum(scores)) / len(scores)

    def _last_state_for_player(self, player_id):
        most_recent_grid_state = self.environment.state()
        players = json.loads(most_recent_grid_state.contents)['players']
        id_matches = [p for p in players if int(p['id']) == player_id]
        if id_matches:
            return id_matches[0]
