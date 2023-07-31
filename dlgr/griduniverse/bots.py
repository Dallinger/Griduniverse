"""Griduniverse bots."""
import datetime
import itertools
import json
import logging
import operator
import random

import gevent
from dallinger.bots import BotBase, HighPerformanceBotBase
from dallinger.config import get_config
from selenium.common.exceptions import (
    NoSuchElementException,
    StaleElementReferenceException,
    WebDriverException,
)
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

from .maze_utils import find_path_astar, maze_to_graph, positions_to_maze

logger = logging.getLogger("griduniverse")


class BaseGridUniverseBot(BotBase):
    """A base class for GridUniverse bots that implements experiment
    specific helper functions and runs under Selenium"""

    MEAN_KEY_INTERVAL = 1  #: The average number of seconds between key presses
    MAX_KEY_INTERVAL = 10  #: The maximum number of seconds between key presses
    END_BUFFER_SECONDS = 30  #: Seconds to wait after expected game end before giving up

    def complete_questionnaire(self):
        """Complete the standard debriefing form randomly."""
        difficulty = Select(self.driver.find_element_by_id("difficulty"))
        difficulty.select_by_value(str(random.randint(1, 7)))
        engagement = Select(self.driver.find_element_by_id("engagement"))
        engagement.select_by_value(str(random.randint(1, 7)))
        try:
            fun = Select(self.driver.find_element_by_id("fun"))
            # This is executed by the IEC_demo.py script...
            # No need to fill out a random value.
            fun.select_by_value(str(0))
        except NoSuchElementException:
            pass
        return True

    def get_wait_time(self):
        """Return a random wait time approximately average to
        MEAN_KEY_INTERVAL but never more than MAX_KEY_INTERVAL"""
        return min(
            random.expovariate(1.0 / self.MEAN_KEY_INTERVAL), self.MAX_KEY_INTERVAL
        )

    def wait_for_grid(self):
        """Blocks until the grid is visible"""
        self.on_grid = True
        return WebDriverWait(self.driver, 15).until(
            EC.presence_of_element_located((By.ID, "grid"))
        )

    def get_js_variable(self, variable_name):
        """Return an arbitrary JavaScript variable from the browser"""
        try:
            script = "return window.{};".format(variable_name)
            result = self.driver.execute_script(script)
            if result is None:
                # In some cases (older remote Firefox)
                # we need to use window.wrappedJSObject
                script = "return window.wrappedJSObject.{};".format(variable_name)
                result = self.driver.execute_script(script)
        except WebDriverException:
            result = None

        if result is not None:
            return json.loads(result)

    def observe_state(self):
        """Return the current state the player sees"""
        return self.get_js_variable("state")

    def get_player_id(self):
        """Return the current player's ID number"""
        return str(self.get_js_variable("ego"))

    @property
    def food_positions(self):
        """Return a list of food coordinates"""
        try:
            return [
                tuple(item["position"])
                for item in self.state["food"]
                if item["maturity"] > 0.5
            ]
        except (AttributeError, TypeError, KeyError):
            return []

    @property
    def wall_positions(self):
        """Return a list of wall coordinates"""
        try:
            return [tuple(item["position"]) for item in self.state["walls"]]
        except (AttributeError, TypeError, KeyError):
            return []

    @property
    def player_positions(self):
        """Return a dictionary that maps player id to their coordinates"""
        return {player["id"]: player["position"] for player in self.state["players"]}

    @property
    def my_position(self):
        """The position of the current player or None if unknown"""
        player_positions = self.player_positions
        if player_positions and self.player_id in player_positions:
            return player_positions[self.player_id]
        else:
            return None

    @property
    def is_still_on_grid(self):
        """Is the grid currently being displayed"""
        return self.on_grid

    def send_next_key(self, grid):
        """Send the next key due to be sent to the server"""
        # This is a roundabout way of sending the key
        # to the grid element; it's needed to avoid a
        # "cannot focus element" error with chromedriver
        try:
            if self.driver.desired_capabilities["browserName"] == "chrome":
                action = ActionChains(self.driver).move_to_element(grid)
                action.click().send_keys(self.get_next_key()).perform()
            else:
                grid.send_keys(self.get_next_key())
        except StaleElementReferenceException:
            self.on_grid = False

    def participate(self):
        """Participate in the experiment.

        Wait a random amount of time, then send a key according to
        the algorithm above.
        """
        self.wait_for_quorum()
        if self._skip_experiment:
            self.log("Participant overrecruited. Skipping experiment.")
            return True
        self.wait_for_grid()
        self.log("Bot player started")

        # Wait for state to be available
        self.state = None
        self.player_id = None
        while (self.state is None) or (self.player_id is None):
            gevent.sleep(0.500)
            self.state = self.observe_state()
            self.player_id = self.get_player_id()

        # Pick an expected finish time far in the future, it will be updated the first time
        # the bot gets a state
        expected_finish_time = datetime.datetime.now() + datetime.timedelta(days=1)

        while self.is_still_on_grid:
            # The proposed finish time is how many seconds we think remain plus the current time
            proposed_finish_time = datetime.datetime.now() + datetime.timedelta(
                seconds=self.grid["remaining_time"]
            )
            # Update the expected finish time iff it is earlier than we thought
            expected_finish_time = min(expected_finish_time, proposed_finish_time)

            # If we expected to finish more than 30 seconds ago then bail out
            now = datetime.datetime.now()
            if (
                expected_finish_time
                + datetime.timedelta(seconds=self.END_BUFFER_SECONDS)
                < now
            ):
                return True

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

    def get_next_key(self):
        """Classes inheriting from this must override this method to provide the logic to
        determine what their next action should be"""
        raise NotImplementedError

    def get_expected_position(self, key):
        """Predict future state given an action.

        Given the current state of players, if we were to push the key
        specified as a parameter, what would we expect the state to become,
        ignoring modeling of other players' behavior.

        :param key: A one character string, especially from
                    :class:`selenium.webdriver.common.keys.Keys`
        """
        positions = self.player_positions
        my_position = self.my_position
        if my_position is None:
            return positions

        if key == Keys.UP:
            my_position = (my_position[0] - 1, my_position[1])
        elif key == Keys.DOWN:
            my_position = (my_position[0] + 1, my_position[1])
        elif key == Keys.LEFT:
            my_position = (my_position[0], my_position[1] - 1)
        elif key == Keys.RIGHT:
            my_position = (my_position[0], my_position[1] + 1)

        if my_position in self.wall_positions:
            # if the new position is in a wall the movement fails
            my_position = self.my_position
        if my_position in self.player_positions.values():
            # If the other position is occupied by a player we assume it fails, but it may not
            my_position = self.my_position

        positions[self.player_id] = my_position
        return positions

    @staticmethod
    def manhattan_distance(coord1, coord2):
        """Return the manhattan (rectilinear) distance between two coordinates."""
        x = coord1[0] - coord2[0]
        y = coord1[1] - coord2[1]
        return abs(x) + abs(y)

    def translate_directions(self, directions):
        """Convert a string of letters representing cardinal directions
        to a tuple of Selenium arrow keys"""
        lookup = {
            "N": Keys.UP,
            "S": Keys.DOWN,
            "E": Keys.RIGHT,
            "W": Keys.LEFT,
        }
        return tuple(map(lookup.get, directions))

    def distance(self, origin, endpoint):
        """Find the number of unit movements needed to
        travel from origin to endpoint, that is the rectilinear distance
        respecting obstacles as well as a tuple of Selenium keys
        that represent this path.

        In particularly difficult mazes this may return an underestimate
        of the true distance and an approximation of the correct path.

        :param origin: The start position
        :type origin: tuple(int, int)
        :param endpoint: The target position
        :type endpoint: tuple(int, int)
        :return: tuple of distance and directions. Distance is None if no route possible.
        :rtype: tuple(int, list(str)) or tuple(None, list(str))
        """
        try:
            maze = self._maze
            graph = self._graph
        except AttributeError:
            self._maze = maze = positions_to_maze(
                self.wall_positions, self.state["rows"], self.state["columns"]
            )
            self._graph = graph = maze_to_graph(maze)
        result = find_path_astar(
            maze, tuple(origin), tuple(endpoint), max_iterations=10000, graph=graph
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


class HighPerformanceBaseGridUniverseBot(HighPerformanceBotBase, BaseGridUniverseBot):
    """A parent class for GridUniverse bots that causes them to be run as a HighPerformanceBot,
    i.e. a bot that does not use Selenium but interacts directly over underlying network
    protocols"""

    _quorum_reached = False

    _skip_experiment = False

    def _make_socket(self):
        """Connect to the Redis server and announce the connection"""
        import dallinger.db
        from dallinger.experiment_server.sockets import chat_backend

        self.redis = dallinger.db.redis_conn
        chat_backend.subscribe(self, "griduniverse")

        self.publish({"type": "connect", "player_id": self.participant_id})

    def send(self, message):
        """Redis handler to receive a message from the griduniverse channel to this bot."""
        channel, payload = message.split(":", 1)
        data = json.loads(payload)
        if channel == "quorum":
            handler = "handle_quorum"
        else:
            handler = "handle_{}".format(data["type"])
        getattr(self, handler, lambda x: None)(data)

    def publish(self, message):
        """Sends a message from this bot to the `griduniverse_ctrl` channel."""
        self.redis.publish("griduniverse_ctrl", json.dumps(message))

    def handle_state(self, data):
        """Receive a grid state update an store it"""
        if "grid" in data:
            # grid is a json encoded dictionary, we want to selectively
            # update this rather than overwrite it as not all grid changes
            # are sent each time (such as food and walls)
            data["grid"] = json.loads(data["grid"])
            if "grid" not in self.grid:
                self.grid["grid"] = {}
            self.grid["grid"].update(data["grid"])
            data["grid"] = self.grid["grid"]
        self.grid.update(data)

    def handle_stop(self, data):
        """Receive an update that the round has finished and mark the
        remaining time as zero"""
        self.grid["remaining_time"] = 0

    def handle_quorum(self, data):
        """Update an instance attribute when the quorum is reached, so it
        can be checked in wait_for_quorum().
        """
        if "q" in data and data["q"] == data["n"]:
            self.log("Quorum fulfilled... unleashing bot.")
            self._quorum_reached = True

    @property
    def is_still_on_grid(self):
        """Returns True if the bot is still on an active grid,
        otherwise False"""
        return self.grid.get("remaining_time", 0) > 0.25

    def send_next_key(self):
        """Determines the message to send that corresponds to
        the requested Selenium key, such that the message is the
        same as the one the browser Javascript would have sent"""
        key = self.get_next_key()
        message = {}
        if key == Keys.UP:
            message = {
                "type": "move",
                "player_id": self.participant_id,
                "move": "up",
            }
        elif key == Keys.DOWN:
            message = {
                "type": "move",
                "player_id": self.participant_id,
                "move": "down",
            }
        elif key == Keys.LEFT:
            message = {
                "type": "move",
                "player_id": self.participant_id,
                "move": "left",
            }
        elif key == Keys.RIGHT:
            message = {
                "type": "move",
                "player_id": self.participant_id,
                "move": "right",
            }
        if message:
            self.publish(message)

    def on_signup(self, data):
        """Take any needed action on response from /participant call."""
        super(HighPerformanceBaseGridUniverseBot, self).on_signup(data)
        # We may have been the player to complete the quorum, in which case
        # we won't have to wait for status from the backend.
        if data["quorum"]["n"] == data["quorum"]["q"]:
            self._quorum_reached = True
        # overrecruitment is handled by web ui, so high perf bots need to
        # do that handling here instead.
        if data["participant"]["status"] == "overrecruited":
            self._skip_experiment = True

    def wait_for_quorum(self):
        """Sleep until a quorum of players has signed up.

        The _quorum_reached attribute is set to True by handle_quorum() upon
        learning from the server that we have a quorum.
        """
        while not self._quorum_reached:
            gevent.sleep(0.001)

    def wait_for_grid(self):
        """Sleep until the game grid is up and running.

        handle_state() will update self.grid when game state messages
        are received from the server.
        """
        self.grid = {}
        self._make_socket()
        while True:
            if self.grid and self.grid["remaining_time"]:
                break
            gevent.sleep(0.001)

    def get_js_variable(self, variable_name):
        """Emulate the state of various JS variables that would be present
        in the browser using our accumulated state.

        The only values of variable_name supported are 'state' and 'ego'"""
        if variable_name == "state":
            return self.grid["grid"]
        elif variable_name == "ego":
            return self.participant_id

    def get_player_id(self):
        """Returns the current player's id"""
        return self.participant_id

    @property
    def question_responses(self):
        return {"engagement": 4, "difficulty": 3, "fun": 3}


class RandomBot(HighPerformanceBaseGridUniverseBot):
    """A bot that plays griduniverse randomly"""

    #: The Selenium keys that this bot will choose between
    VALID_KEYS = [Keys.UP, Keys.DOWN, Keys.RIGHT, Keys.LEFT, Keys.SPACE, "r", "b", "y"]

    def get_next_key(self):
        """Randomly press one of Up, Down, Left, Right, space, r, b or y"""
        return random.choice(self.VALID_KEYS)


class FoodSeekingBot(HighPerformanceBaseGridUniverseBot):
    """A bot that actively tries to increase its score.

    The bot moves towards the closest food.
    """

    def __init__(self, *args, **kwargs):
        super(FoodSeekingBot, self).__init__(*args, **kwargs)
        self.target_coordinates = (None, None)

    def get_logical_targets(self):
        """Find a logical place to move.

        When run on a page view that has data extracted from the grid state
        find the best targets for each of the players, where the best target
        is the closest item of food.
        """
        best_choice = 100e10, None
        position = self.my_position
        if position is None:
            return {}
        for j, food in enumerate(self.food_positions):
            distance, _ = self.distance(position, food)
            if distance and distance < best_choice[0]:
                best_choice = distance, j
        return {self.player_id: best_choice[1]}

    def get_next_key(self):
        """Returns the best key to press in order to maximize point scoring, as follows:

        If there is food on the grid and the bot is not currently making its way
        towards a piece of food, find the logical target and store that coordinate
        as the current target.

        If there is a current target and there is food there, move towards that target
        according to the optimal route, taking walls into account.

        If there is a current target but no food there, unset the target and follow
        the method normally.
        ]
        If there is no food on the grid, move away from other players, such that
        the average distance between players is maximized. This makes it more
        likely that players have an equal chance at finding new food items.

        If there are no actions that get the player nearer to food or increase
        player spread, press a random key."""
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
            # Otherwise, move randomly avoiding walls
            for key in (Keys.UP, Keys.DOWN, Keys.LEFT, Keys.RIGHT):
                expected = self.get_expected_position(key)
                if expected != my_position:
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


class AdvantageSeekingBot(HighPerformanceBaseGridUniverseBot):
    """A bot that actively tries to increase its score.

    The bot moves towards the closest food that aren't the logical
    target for another player.
    """

    def __init__(self, *args, **kwargs):
        super(AdvantageSeekingBot, self).__init__(*args, **kwargs)
        self.target_coordinates = (None, None)

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
                if distance is None:
                    # This food item is unreachable
                    continue
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
        for player_id, food_id in best_choices:
            if player_id in seen_players:
                continue
            if food_id in seen_food:
                continue
            seen_players.add(player_id)
            seen_food.add(food_id)
            choices[player_id] = food_id
        return choices

    def get_next_key(self):
        """Returns the best key to press in order to maximize point scoring, as follows:

        If there is food on the grid and the bot is not currently making its way
        towards a piece of food, find the logical target and store that coordinate
        as the current target.

        If there is a current target and there is food there, move towards that target
        according to the optimal route, taking walls into account.

        If there is a current target but no food there, unset the target and follow
        the method normally.
        ]
        If there is no food on the grid, move away from other players, such that
        the average distance between players is maximized. This makes it more
        likely that players have an equal chance at finding new food items.

        If there are no actions that get the player nearer to food or increase
        player spread, press a random key."""
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


def Bot(*args, **kwargs):
    """Pick a bot implementation based on a configuration parameter.

    This can be set in config.txt in this directory or by environment variable.
    """

    config = get_config()
    bot_implementation = config.get("bot_policy", "RandomBot")
    bot_class = globals().get(bot_implementation, None)
    if bot_class and issubclass(bot_class, BotBase):
        return bot_class(*args, **kwargs)
    else:
        raise NotImplementedError
