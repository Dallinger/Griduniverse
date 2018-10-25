import json
import mock
import pytest

from selenium.webdriver.common.keys import Keys

from dlgr.griduniverse.bots import RandomBot, AdvantageSeekingBot


@pytest.fixture
def overrecruited_response():
    return {
        'status': 'OK',
        'participant': {
            'id': 4,
            'status': 'overrecruited'
        },
        'quorum': {
            'q': 1,
            'n': 1,
            'overrecruited': True
        }
    }


@pytest.fixture
def working_response():
    return {
        'status': 'OK',
        'participant': {
            'id': 4,
            'status': 'working'
        },
        'quorum': {
            'q': 5,
            'n': 1,
            'overrecruited': False
        }
    }


@pytest.fixture
def grid_state():
    # WWWWWWWWWW
    # WF.W.....W
    # W.2W.....W
    # WWWW.....W
    # W.FWF....W
    # W..W.1...W
    # W..W.....W
    # W..W.....W
    # W........W
    # WWWWWWWWWW
    food_positions = [
        {
            u'color': [0.534, 0.591, 0.087],
            u'id': food_id,
            u'maturity': 0.9,
            u'position': position
        } for food_id, position in enumerate([
            [1, 1],
            [2, 4],
            [4, 4]
        ])
    ]
    wall_positions = [
        [3, 1],
        [3, 2],
        [3, 3],
        [3, 4],
        [3, 5],
        [3, 6],
        [3, 7],
        [2, 3],
        [1, 3],
    ]
    for i in range(10):
        # Add bounding box
        wall_positions.append([i, 0])
        wall_positions.append([i, 9])
        wall_positions.append([0, i])
        wall_positions.append([9, i])
    wall_positions = [
        {u'color': [0.5, 0.5, 0.5], u'position': position} for position in wall_positions
    ]
    grid_data = {
        u'columns': 10,
        u'donation_active': False,
        u'food': food_positions,
        u'players': [
            {
                u'color': u'RED',
                u'id': 1,
                u'identity_visible': True,
                u'motion_auto': False,
                u'motion_direction': u'right',
                u'motion_speed_limit': 8,
                u'motion_timestamp': 0,
                u'name': u'Jeanne Brown',
                u'payoff': 0.0,
                u'position': [5, 5],
                u'score': 0.0
            },
            {
                u'color': u'BLUE',
                u'id': 2,
                u'identity_visible': True,
                u'motion_auto': False,
                u'motion_direction': u'right',
                u'motion_speed_limit': 8,
                u'motion_timestamp': 0,
                u'name': u'Kelsey Houston',
                u'payoff': 0.0,
                u'position': [2, 2],
                u'score': 0.0
            }
        ],
        u'round': 0,
        u'rows': 10,
        u'walls': wall_positions}

    return json.dumps(grid_data)


class TestRandomMovementBot(object):

    @pytest.fixture
    def bot(self):
        b = RandomBot('http://example.com')
        b.publish = mock.Mock()
        return b

    def test_random_bot_selects_random_key(self, bot):
        assert len(bot.VALID_KEYS) == 8
        assert Keys.UP in bot.VALID_KEYS
        assert Keys.DOWN in bot.VALID_KEYS
        assert Keys.RIGHT in bot.VALID_KEYS
        assert Keys.LEFT in bot.VALID_KEYS
        for i in range(30):
            assert bot.get_next_key() in bot.VALID_KEYS

    def test_random_bot_sends_random_key(self, bot):
        bot.VALID_KEYS = [Keys.DOWN, ]
        bot.publish.assert_not_called()
        bot.send_next_key()
        bot.publish.assert_called_once_with(
            {'type': 'move', 'player_id': '', 'move': 'down'}
        )

    def test_skips_experiment_if_overrecruited(self, bot, overrecruited_response):
        bot.on_signup(overrecruited_response)

        assert bot._skip_experiment
        assert bot.participate()  # Harmless no-op

    def test_runs_experiment_if_not_overrecruited(self, bot, working_response):
        bot.on_signup(working_response)

        assert not bot._skip_experiment


class TestAdvantageSeekingBot(object):

    @pytest.fixture
    def bot(self):
        return AdvantageSeekingBot('http://example.com')

    @pytest.fixture
    def bot_in_maze(self, bot, grid_state):
        bot.grid = {}
        bot.participant_id = 1
        bot.handle_state({'grid': grid_state})
        bot.state = bot.observe_state()
        return bot

    def test_skips_experiment_if_overrecruited(self, bot, overrecruited_response):
        bot.on_signup(overrecruited_response)

        assert bot._skip_experiment
        assert bot.participate()  # Harmless no-op

    def test_runs_experiment_if_not_overrecruited(self, bot, working_response):
        bot.on_signup(working_response)

        assert not bot._skip_experiment

    def test_advantage_seeking_bot_understands_distances(self, bot_in_maze):
        assert bot_in_maze.food_positions == [(1, 1), (2, 4), (4, 4)]
        assert bot_in_maze.player_positions == {1: [5, 5], 2: [2, 2]}
        assert bot_in_maze.distances() == {
            1: {
                0: None,
                1: 10,
                2: 2
            }, 2: {
                0: 2,
                1: None,
                2: None
            }
        }

    def test_advantage_seeking_bot_goes_for_closest_food(self, bot_in_maze):
        bot_in_maze.player_id = 1
        assert bot_in_maze.get_next_key() == Keys.UP
        assert bot_in_maze.target_coordinates == (4, 4)
        bot_in_maze.player_id = 2
        bot_in_maze.target_coordinates = (None, None)
        assert bot_in_maze.get_next_key() == Keys.UP
        assert bot_in_maze.target_coordinates == (1, 1)
