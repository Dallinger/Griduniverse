"""Griduniverse bots."""
import itertools
import json
import logging
import operator
import random
import time

import gevent
from selenium.common.exceptions import StaleElementReferenceException
from selenium.common.exceptions import WebDriverException
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support.ui import Select

from dallinger.bots import BotBase, HighPerformanceBotBase
from dallinger.config import get_config

from .maze_utils import positions_to_maze, maze_to_graph, find_path_astar

logger = logging.getLogger('griduniverse')
config = get_config()


class BaseGridUniverseBot(BotBase):

    MEAN_KEY_INTERVAL = 1
    MAX_KEY_INTERVAL = 10

    def get_wait_time(self):
        return min(random.expovariate(1.0 / self.MEAN_KEY_INTERVAL), self.MAX_KEY_INTERVAL)

    def wait_for_grid(self):
        self.on_grid = True
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

    def get_player_id(self):
        return str(self.get_js_variable("ego"))

    @property
    def food_positions(self):
        try:
            return [tuple(item['position']) for item in self.state['food']
                    if item['maturity'] > 0.5]
        except (AttributeError, TypeError, KeyError):
            return []

    @property
    def wall_positions(self):
        try:
            return [tuple(item['position']) for item in self.state['walls']]
        except (AttributeError, TypeError, KeyError):
            return []

    @property
    def player_positions(self):
        return {
            player['id']: player['position'] for player in self.state['players']
        }

    @property
    def my_position(self):
        player_positions = self.player_positions
        if player_positions and self.player_id in player_positions:
            return player_positions[self.player_id]
        else:
            return None

    @property
    def is_still_on_grid(self):
        return self.on_grid

    def send_next_key(self, grid):
        # This is a roundabout way of sending the key
        # to the grid element; it's needed to avoid a
        # "cannot focus element" error with chromedriver
        try:
            if self.driver.desired_capabilities['browserName'] == 'chrome':
                action = ActionChains(self.driver).move_to_element(grid)
                action.click().send_keys(self.get_next_key()).perform()
            else:
                grid.send_keys(self.get_next_key())
        except StaleElementReferenceException:
            self.on_grid = False


class HighPerformanceBaseGridUniverseBot(HighPerformanceBotBase, BaseGridUniverseBot):

    _quorum_reached = False

    def _make_socket(self):
        from dallinger.heroku.worker import conn
        self.redis = conn

        from dallinger.experiment_server.sockets import chat_backend
        chat_backend.subscribe(self, 'griduniverse')

        self.publish({
            'type': 'connect',
            'player_id': self.participant_id
        })

    def send(self, message):
        """Sends a message from the griduniverse channel to this bot."""
        channel, payload = message.split(':', 1)
        data = json.loads(payload)
        if channel == 'quorum':
            handler = 'handle_quorum'
        else:
            handler = 'handle_{}'.format(data['type'])
        getattr(self, handler, lambda x: None)(data)

    def publish(self, message):
        """Sends a message from this bot to the griduniverse_ctrl channel."""
        self.redis.publish('griduniverse_ctrl', json.dumps(message))

    def handle_state(self, data):
        if 'grid' in data:
            # grid is a json encoded dictionary, we want to selectively
            # update this rather than overwrite it as not all grid changes
            # are sent each time (such as food and walls)
            data['grid'] = json.loads(data['grid'])
            if 'grid' not in self.grid:
                self.grid['grid'] = {}
            self.grid['grid'].update(data['grid'])
            data['grid'] = self.grid['grid']
        self.grid.update(data)

    def handle_stop(self, data):
        self.grid['remaining_time'] = 0

    def handle_quorum(self, data):
        """Update an instance attribute when the quorum is reached, so it
        can be checked in wait_for_quorum().
        """
        if 'q' in data and data['q'] == data['n']:
            self.log("Quorum fulfilled... unleashing bot.")
            self._quorum_reached = True

    @property
    def is_still_on_grid(self):
        return self.grid.get('remaining_time', 0) > 0.25

    def send_next_key(self):
        key = self.get_next_key()
        message = {}
        if key == Keys.UP:
            message = {
                'type': "move",
                'player_id': self.participant_id,
                'move': 'up',
            }
        elif key == Keys.DOWN:
            message = {
                'type': "move",
                'player_id': self.participant_id,
                'move': 'down',
            }
        elif key == Keys.LEFT:
            message = {
                'type': "move",
                'player_id': self.participant_id,
                'move': 'left',
            }
        elif key == Keys.RIGHT:
            message = {
                'type': "move",
                'player_id': self.participant_id,
                'move': 'right',
            }
        if message:
            self.publish(message)

    def on_signup(self, data):
        """Take any needed action on response from /participant call."""
        super(HighPerformanceBaseGridUniverseBot, self).on_signup(data)
        # We may have been the player to complete the quorum, in which case
        # we won't have to wait for status from the backend.
        if data['quorum']['n'] == data['quorum']['q']:
            self._quorum_reached = True

    def wait_for_quorum(self):
        """Sleep until a quorum of players has signed up.

        The _quorum_reached attribute is set to True by handle_quorum() upon
        learning from the backend that we have a quorum.
        """
        while not self._quorum_reached:
            gevent.sleep(0.001)

    def wait_for_grid(self):
        """Sleep until the game grid is up and running.

        handle_state() will update self.grid when game state messages
        are received from the backend.
        """
        self.grid = {}
        self._make_socket()
        while True:
            if self.grid and self.grid['remaining_time']:
                break
            gevent.sleep(0.001)

    def get_js_variable(self, variable_name):
        # Emulate the state of various JS variables that would be present
        # in the frontend using our accumulated state
        if variable_name == 'state':
            return self.grid['grid']
        elif variable_name == 'ego':
            return self.participant_id

    def get_player_id(self):
        return self.participant_id


class RandomBot(HighPerformanceBaseGridUniverseBot):
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

    def get_next_key(self):
        return random.choice(self.VALID_KEYS)

    def participate(self):
        """Participate by randomly hitting valid keys"""
        self.wait_for_quorum()
        self.wait_for_grid()
        self.log('Bot player started')
        while self.is_still_on_grid:
            time.sleep(self.get_wait_time())
            self.send_next_key()
        self.log('Bot player stopped.')
        return True


class AdvantageSeekingBot(HighPerformanceBaseGridUniverseBot):
    """A bot that seeks an advantage.

    The bot moves towards the food it has the biggest advantage over the other
    players at getting.
    """

    def __init__(self, *args, **kwargs):
        super(AdvantageSeekingBot, self).__init__(*args, **kwargs)
        self.target_coordinates = (None, None)

    def get_logical_targets(self):
        """Find a logical place to move.

        When run on a page view that has data extracted from the grid state
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
        """Mean distance between players.

        When run after populating state data, this returns the mean
        distance between all players on the board, to be used as a heuristic
        for 'spreading out' if there are no logical targets.
        """
        # Allow passing positions in, to calculate the spread of a hypothetical
        # future state, rather than the current state
        if positions is None:
            positions = self.player_positions
        positions = positions.values()
        # Find the distances between all pairs of players
        pairs = itertools.combinations(positions, 2)
        distances = itertools.starmap(self.manhattan_distance, pairs)
        # Calculate and return the mean. distances is an iterator, so we
        # convert it to a tuple so we can more easily do sums on its data
        distances = tuple(distances)
        if distances:
            return float(sum(distances)) / len(distances)
        else:
            # There is only one player, so there are no distances between
            # players.
            return 0

    def get_expected_position(self, key):
        """Predict future state given an action.

        Given the current state of players, if we were to push the key
        specified as a parameter, what would we expect the state to become,
        ignoring modeling of other players' behavior
        """
        positions = self.player_positions
        my_position = self.my_position
        if my_position is None:
            return positions
        pad = 5
        rows = self.state['rows']
        if key == Keys.UP and my_position[0] > pad:
            my_position = (my_position[0] - 1, my_position[1])
        if key == Keys.DOWN and my_position[0] < (rows - pad):
            my_position = (my_position[0] + 1, my_position[1])
        if key == Keys.LEFT and my_position[1] > pad:
            my_position = (my_position[0], my_position[1] - 1)
        if key == Keys.RIGHT and my_position[1] < (rows - pad):
            my_position = (my_position[0], my_position[1] + 1)
        positions[self.player_id] = my_position
        return positions

    def get_next_key(self):
        valid_keys = []
        my_position = self.my_position
        try:
            if self.target_coordinates in self.food_positions:
                food_position = self.target_coordinates
            else:
                # If there is a most logical target, we move towards it
                target_id = self.get_logical_targets()[self.player_id]
                food_position = self.food_positions[target_id]
                self.target_coordinates = food_position
        except KeyError:
            # Otherwise, move in a direction that increases average spread.
            current_spread = self.get_player_spread()
            for key in (Keys.UP, Keys.DOWN, Keys.LEFT, Keys.RIGHT):
                expected = self.get_expected_position(key)
                if self.get_player_spread(expected) > current_spread:
                    valid_keys.append(key)
        else:
            baseline_distance, directions = self.distance(my_position, food_position)
            if baseline_distance:
                valid_keys.append(directions[0])
        if not valid_keys:
            # If there are no food items available and no movement would
            # cause the average spread of players to increase, fall back to
            # the behavior of the RandomBot
            valid_keys = RandomBot.VALID_KEYS
        return random.choice(valid_keys)

    @staticmethod
    def manhattan_distance(coord1, coord2):
        x = coord1[0] - coord2[0]
        y = coord1[1] - coord2[1]
        return abs(x) + abs(y)

    def translate_directions(self, directions):
        lookup = {
            'N': Keys.UP,
            'S': Keys.DOWN,
            'E': Keys.RIGHT,
            'W': Keys.LEFT,
        }
        return tuple(map(lookup.get, directions))

    def distance(self, origin, endpoint):
        try:
            maze = self._maze
            graph = self._graph
        except AttributeError:
            self._maze = maze = positions_to_maze(
                self.wall_positions,
                self.state['rows'],
                self.state['columns']
            )
            self._graph = graph = maze_to_graph(maze)
        result = find_path_astar(
            maze,
            tuple(origin),
            tuple(endpoint),
            max_iterations=10000,
            graph=graph
        )
        if result:
            distance = result[0]
            directions = self.translate_directions(result[1])
            return distance, directions
        else:
            return None, []

    def distances(self):
        """Compute distances to food.

        Returns a dictionary keyed on player_id, with the value being another
        dictionary which maps the index of a food item in the positions list
        to the distance between that player and that food item.
        """
        distances = {}
        for player_id, position in self.player_positions.items():
            player_distances = {}
            for j, food in enumerate(self.food_positions):
                player_distances[j], _ = self.distance(position, food)
            distances[player_id] = player_distances
        return distances

    def participate(self):
        """Participate in the experiment.

        Wait a random amount of time, then send a key according to
        the algorithm above.
        """
        self.wait_for_quorum()
        self.wait_for_grid()
        self.log('Bot player started')

        # Wait for state to be available
        self.state = None
        self.player_id = None
        while (self.state is None) or (self.player_id is None):
            gevent.sleep(0.500)
            self.state = self.observe_state()
            self.player_id = self.get_player_id()

        while self.is_still_on_grid:
            gevent.sleep(self.get_wait_time())
            try:
                observed_state = self.observe_state()
                if observed_state:
                    self.state = observed_state
                    self.send_next_key()
                else:
                    return False
            except (StaleElementReferenceException, AttributeError):
                return True

        self.log('Bot player stopped')

    def complete_questionnaire(self):
        """Complete the standard debriefing form randomly."""
        difficulty = Select(self.driver.find_element_by_id('difficulty'))
        difficulty.select_by_value(str(random.randint(1, 7)))
        engagement = Select(self.driver.find_element_by_id('engagement'))
        engagement.select_by_value(str(random.randint(1, 7)))
        try:
            fun = Select(self.driver.find_element_by_id('fun'))
            # This is executed by the IEC_demo.py script...
            # No need to fill out a random value.
            fun.select_by_value(str(0))
        except NoSuchElementException:
            pass
        return True


def Bot(*args, **kwargs):
    """Pick a bot implementation based on a configuration parameter.

    This can be set in config.txt in this directory or by environment variable.
    """

    bot_implementation = config.get('bot_policy', u'RandomBot')
    bot_class = globals().get(bot_implementation, None)
    if bot_class and issubclass(bot_class, BotBase):
        return bot_class(*args, **kwargs)
    else:
        raise NotImplementedError
