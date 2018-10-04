"""
Tests for `dlgr.griduniverse` module.
"""
import collections
import json
import mock
import pytest
import time


class TestDependenciesLoaded(object):

    def test_odo_importable(self):
        import odo
        assert odo is not None

    def test_tablib_importable(self):
        import tablib
        assert tablib is not None


@pytest.mark.usefixtures('env')
class TestExperimentClass(object):

    def test_initialization(self, exp):
        from dallinger.experiment import Experiment
        assert isinstance(exp, Experiment)

    def test_recruiter_property_is_some_subclass_of_recruiter(self, exp):
        from dallinger.recruiters import Recruiter
        assert isinstance(exp.recruiter, Recruiter)

    def test_new_experiment_has_a_grid(self, exp):
        from dlgr.griduniverse.experiment import Gridworld
        assert isinstance(exp.grid, Gridworld)

    def test_create_network_builds_default_network_type(self, exp):
        from dallinger.networks import FullyConnected
        net = exp.create_network()
        assert isinstance(net, FullyConnected)

    def test_session_is_dallinger_global(self, exp, db_session):
        assert exp.session() is db_session()

    def test_socket_session_is_not_dallinger_global(self, exp, db_session):
        # Experiment creates socket_session
        assert exp.socket_session() is not db_session()

    def test_environment_uses_experiments_networks(self, exp):
        exp.environment.network in exp.networks()

    def test_recruit_does_not_raise(self, exp):
        exp.recruit()

    def test_game_loop(self, exp):
        exp.grid = mock.Mock()
        exp.grid.num_food = 10
        exp.grid.round = 0
        exp.grid.seasonal_growth_rate = 1
        exp.grid.food_growth_rate = 1.0
        exp.grid.rows = exp.grid.columns = 25
        exp.grid.players = {'1': mock.Mock()}
        exp.grid.players['1'].score = 10
        exp.grid.contagion = 1
        exp.grid.tax = 1.0
        exp.grid.food_locations = []
        exp.grid.frequency_dependence = 1
        exp.grid.frequency_dependent_payoff_rate = 0
        exp.socket_session = mock.Mock()
        exp.publish = mock.Mock()
        with mock.patch('gevent.sleep') as _fake_sleep:
            def count_down(counter):
                if counter[0] <= 0:
                    return True
                counter[0] -= 1
                return False
            start_counter = [3]
            end_counter = [3]
            # Each of these will loop three times before while condition is met
            type(exp.grid).game_started = mock.PropertyMock(
                side_effect=lambda: count_down(start_counter)
            )
            type(exp.grid).game_over = mock.PropertyMock(
                side_effect=lambda: count_down(end_counter)
            )
            exp.grid.serialize.return_value = {}
            # Set start time to a few seconds ago to trigger one round of
            # time-based events
            exp.grid.start_timestamp = time.time() - 2

            exp.game_loop()
            # labryinth built once
            assert exp.grid.build_labyrinth.call_count == 1
            # Spawn food called twice for each num_food, once at start and again
            # on timed events to replenish empty list
            assert exp.grid.spawn_food.call_count == exp.grid.num_food * 2
            # Grid serialized and added to DB session once per loop
            assert exp.grid.serialize.call_count == 3
            assert exp.socket_session.add.call_count == 3
            # Session commited once per loop and again at end
            assert exp.socket_session.commit.call_count == 4
            # Wall and food state unset, food count reset
            assert exp.grid.walls_updated is False
            assert exp.grid.food_updated is False
            assert exp.grid.num_food == 10
            # Player has been taxed one point during the timed event round
            assert exp.grid.players['1'].score == 9.0
            # Payoffs computed once per loop before checking round completion
            assert exp.grid.compute_payoffs.call_count == 3
            assert exp.grid.check_round_completion.call_count == 3
            # publish called at end of round with stop event
            exp.publish.assert_called_once_with({'type': 'stop'})

    def test_send_state_thread(self, exp):
        exp.grid = mock.Mock()
        exp.grid.walls_density = 0
        exp.grid.players = {'1': mock.Mock()}
        exp.publish = mock.Mock()
        with mock.patch('gevent.sleep') as _fake_sleep:
            def count_down(counter):
                if counter[0] <= 0:
                    return True
                counter[0] -= 1
                return False
            end_counter = [2]
            # This will loop 3 times before the loop is broken
            type(exp.grid).game_over = mock.PropertyMock(
                side_effect=lambda: count_down(end_counter)
            )
            exp.grid.serialize.return_value = {
                'grid': 'serialized',
                'walls': [],
                'food': [],
                'players': [{'id': '1'}],
            }

            exp.send_state_thread()
            # Grid serialized once per loop
            assert exp.grid.serialize.call_count == 3
            # publish called with grid state message once per loop
            assert exp.publish.call_count == 3


@pytest.mark.usefixtures('env')
class TestGridWorld(object):

    @pytest.fixture
    def gridworld(self, fresh_gridworld, active_config):
        from dlgr.griduniverse.experiment import Gridworld
        gw = Gridworld(
            log_event=mock.Mock(),
            **active_config.as_dict()
        )
        yield gw

    def test_spawn_food(self, gridworld):
        # reset food state
        gridworld.food_updated = False
        assert len(gridworld.food_locations.keys()) == 0
        assert gridworld.food_locations.get((0, 0)) is None
        # Spawn food at specific location
        gridworld.spawn_food(position=(0, 0))
        assert gridworld.food_updated is True
        assert gridworld.food_locations.get((0, 0)) is not None
        # Spawn food at random location with no arguments
        gridworld.spawn_food()
        assert len(gridworld.food_locations.keys()) == 2

    def test_serialize(self, gridworld):
        player = mock.Mock()
        player.serialize.return_value = 'Serialized Player'
        gridworld.players = {1: player}
        values = gridworld.serialize()
        assert values['players'] == ['Serialized Player']
        assert values['round'] == 0
        assert values['donation_active'] == gridworld.donation_active
        assert values['rows'] == gridworld.rows
        assert values['columns'] == gridworld.columns

        # Walls and food are included by default but can be excluded
        assert values.get('walls') == []
        assert values.get('food') == []
        wall = mock.Mock()
        food = mock.Mock()
        wall.serialize.return_value = 'Serialized Wall'
        food.serialize.return_value = 'Serialized Food'
        gridworld.wall_locations[(1, 1)] = wall
        gridworld.food_locations[(2, 2)] = food
        values = gridworld.serialize()
        assert values.get('walls') == ['Serialized Wall']
        assert values.get('food') == ['Serialized Food']

        values = gridworld.serialize(include_walls=False)
        assert values.get('walls') is None
        values = gridworld.serialize(include_food=False)
        assert values.get('food') is None

    def test_check_round_completion(self, gridworld, active_config):
        # Game hasn't started
        gridworld.num_rounds = 2
        gridworld._start_if_ready()
        gridworld.check_round_completion()
        assert gridworld.round == 0
        assert gridworld.start_timestamp is None
        assert gridworld.remaining_round_time == 0
        assert gridworld.game_over is False

        # Adding players starts the game
        gridworld.players = {1: mock.Mock()}
        gridworld._start_if_ready()
        gridworld.check_round_completion()
        assert gridworld.start_timestamp is not None
        assert round(gridworld.remaining_round_time) == round(gridworld.time_per_round)
        assert gridworld.round == 0

        # When elapsed_round_time surpasses the time_per_round, the round is over
        with mock.patch('time.time') as mod_time:
            start_time = gridworld.start_timestamp
            mod_time.return_value = start_time + gridworld.time_per_round
            assert gridworld.remaining_round_time == 0
            gridworld.check_round_completion()
            assert gridworld.round == 1
            assert gridworld.remaining_round_time == 300
            assert gridworld.game_over is False
            # Round start time has been updated
            assert gridworld.start_timestamp == start_time + gridworld.time_per_round
            # Player motion timestamp has been set
            assert gridworld.players[1].motion_timestamp == 0

            # Finish final round
            start_time = gridworld.start_timestamp
            mod_time.return_value = start_time + gridworld.time_per_round
            gridworld.check_round_completion()
            assert gridworld.remaining_round_time == 0
            assert gridworld.game_over is True

    def test_instructions(self, gridworld):
        # There are a number of parameters that influence the game instructions
        # new parameters that influence game play should be included here
        boolean_params = (
            'build_walls', 'others_visible', 'mutable_colors',
            'player_overlap', 'motion_auto',
            'respawn_food', 'food_planting',
            'show_chatroom', 'pseudonyms'
        )
        numeric_params = (
            'window_columns', 'window_rows', 'walls_density',
            'num_rounds', 'num_players', 'num_colors', 'contagion',
            'visibility', 'motion_cost', 'motion_tremble_rate',
            'food_maturation_threshold', 'donation_amount',
            'dollars_per_point'
        )
        dependent_numeric_params = (
            'wall_building_cost', 'food_planting_cost'
        )
        dependent_boolean_params = (
            'frequency_dependence', 'alternate_consumption_donation'
        )

        instructions = gridworld.instructions()
        for param in boolean_params:
            # invert the parameter value
            setattr(gridworld, param, not getattr(gridworld, param, False))
            assert gridworld.instructions() != instructions, (
                '{} = {} did not change instructions'.format(
                    param, getattr(gridworld, param))
            )
            instructions = gridworld.instructions()

        for param in numeric_params:
            old_value = getattr(gridworld, param, 0)
            # Add one or subtract 20 depending on original value
            new_value = old_value + 1 - max((old_value - 21), 0)
            setattr(gridworld, param, new_value)
            assert gridworld.instructions() != instructions, (
                '{} = {} did not change instructions'.format(
                    param, getattr(gridworld, param))
            )
            instructions = gridworld.instructions()

        # These are parameters that only have an effect if a numeric value above
        # has been set
        for param in dependent_boolean_params:
            # invert the parameter value
            setattr(gridworld, param, not getattr(gridworld, param, False))
            assert gridworld.instructions() != instructions, (
                '{} = {} did not change instructions'.format(
                    param, getattr(gridworld, param))
            )
            instructions = gridworld.instructions()

        # These are generally costs for things enabled above
        for param in dependent_numeric_params:
            # increment the cost
            setattr(gridworld, param, getattr(gridworld, param, 0) + 1)
            assert gridworld.instructions() != instructions, (
                '{} = {} did not change instructions'.format(
                    param, getattr(gridworld, param))
            )
            instructions = gridworld.instructions()


@pytest.mark.usefixtures('env', 'fake_gsleep')
class TestGameLoops(object):

    @pytest.fixture
    def loop_exp_3x(self, exp):
        exp.grid = mock.Mock()
        exp.grid.num_food = 10
        exp.grid.round = 0
        exp.grid.seasonal_growth_rate = 1
        exp.grid.food_growth_rate = 1.0
        exp.grid.rows = exp.grid.columns = 25
        exp.grid.players = {'1': mock.Mock()}
        exp.grid.players['1'].score = 10
        exp.grid.contagion = 1
        exp.grid.tax = 1.0
        exp.grid.food_locations = []
        exp.grid.frequency_dependence = 1
        exp.grid.frequency_dependent_payoff_rate = 0
        exp.grid.start_timestamp = time.time()
        exp.socket_session = mock.Mock()
        exp.publish = mock.Mock()
        exp.grid.serialize.return_value = {}

        def count_down(counter):
            for c in counter:
                return False
            return True
        end_counter = (i for i in range(3))
        start_counter = (i for i in range(3))
        # Each of these will loop three times before while condition is met
        type(exp.grid).game_started = mock.PropertyMock(
            side_effect=lambda: count_down(start_counter)
        )
        type(exp.grid).game_over = mock.PropertyMock(
            side_effect=lambda: count_down(end_counter)
        )
        yield exp

    def test_loop_builds_labrynth(self, loop_exp_3x):
        exp = loop_exp_3x
        exp.game_loop()
        # labryinth built once
        assert exp.grid.build_labyrinth.call_count == 1

    def test_loop_spawns_food(self, loop_exp_3x):
        exp = loop_exp_3x
        exp.game_loop()
        # Spawn food called once for each num_food
        assert exp.grid.spawn_food.call_count == exp.grid.num_food

    def test_loop_spawns_food_during_timed_events(self, loop_exp_3x):
        # Spawn food called twice for each num_food, once at start and again
        # on timed events to replenish empty list
        exp = loop_exp_3x

        # Ensure one timed events round
        exp.grid.start_timestamp -= 2

        exp.game_loop()
        assert exp.grid.spawn_food.call_count == exp.grid.num_food * 2

    def test_loop_serialized_and_saves(self, loop_exp_3x):
        # Grid serialized and added to DB session once per loop
        exp = loop_exp_3x
        exp.game_loop()
        assert exp.grid.serialize.call_count == 3
        assert exp.socket_session.add.call_count == 3
        # Session commited once per loop and again at end
        assert exp.socket_session.commit.call_count == 4

    def test_loop_resets_state(self, loop_exp_3x):
        # Wall and food state unset, food count reset during loop
        exp = loop_exp_3x
        exp.game_loop()
        assert exp.grid.walls_updated is False
        assert exp.grid.food_updated is False

    def test_loop_taxes_points(self, loop_exp_3x):
        # Player is taxed one point during the timed event round
        exp = loop_exp_3x

        # Ensure one timed events round
        exp.grid.start_timestamp -= 2

        exp.game_loop()
        assert exp.grid.players['1'].score == 9.0

    def test_loop_computes_payoffs(self, loop_exp_3x):
        # Payoffs computed once per loop before checking round completion
        exp = loop_exp_3x
        exp.game_loop()
        assert exp.grid.compute_payoffs.call_count == 3
        assert exp.grid.check_round_completion.call_count == 3

    def test_loop_publishes_stop_event(self, loop_exp_3x):
        # publish called with stop event at end of round
        exp = loop_exp_3x
        exp.game_loop()
        exp.publish.assert_called_once_with({'type': 'stop'})

    def test_send_state_thread(self, loop_exp_3x):
        # State thread will loop 4 times before the loop is broken
        exp = loop_exp_3x
        exp.grid.serialize.return_value = {
            'grid': 'serialized',
            'walls': [],
            'food': [],
            'players': [{'id': '1'}],
        }

        exp.send_state_thread()
        # Grid serialized once per loop
        assert exp.grid.serialize.call_count == 4
        # publish called with grid state message once per loop
        assert exp.publish.call_count == 4


@pytest.mark.usefixtures('env')
class TestPlayerConnects(object):

    def test_handle_connect_creates_node(self, exp, a):
        participant = a.participant()
        exp.handle_connect({'player_id': participant.id})
        assert participant.id in exp.node_by_player_id

    def test_handle_connect_adds_player_to_grid(self, exp, a):
        participant = a.participant()
        exp.handle_connect({'player_id': participant.id})
        assert participant.id in exp.grid.players

    def test_handle_connect_is_noop_for_spectators(self, exp):
        exp.handle_connect({'player_id': 'spectator'})
        assert exp.node_by_player_id == {}

    def test_colors_distributed_evenly(self, exp, participants):
        exp.grid.num_players = 9
        exp.networks()[0].max_size = 10
        players = [
            exp.handle_connect({'player_id': participant.id}) or exp.grid.players[participant.id]
            for participant in participants[:9]
        ]
        colors = collections.Counter([player.color_idx for player in players])
        assert colors == {0: 3, 1: 3, 2: 3}

    def test_colors_distributed_almost_evenly_if_on_edge(self, exp, participants):
        exp.grid.num_colors = 2
        exp.grid.num_players = 9
        exp.networks()[0].max_size = 10
        players = [
            exp.handle_connect({'player_id': participant.id}) or exp.grid.players[participant.id]
            for participant in participants[:9]
        ]
        colors = collections.Counter([player.color_idx for player in players])
        assert colors == {0: 5, 1: 4}


@pytest.mark.usefixtures('env')
class TestRecordsPlayerActivity(object):

    def test_records_player_events(self, exp, a):
        participant = a.participant()
        exp.handle_connect({'player_id': participant.id})
        exp.send(
            'griduniverse_ctrl:'
            '{{"type":"move","player_id":{},"move":"left"}}'.format(participant.id)
        )
        time.sleep(10)
        data = exp.retrieve_data()
        # Get the last recorded event
        event_detail = json.loads(data.infos.df['details'].values[-1])
        assert event_detail['player_id'] == participant.id
        assert event_detail['move'] == 'left'

    def test_scores_and_payoffs_averaged(self, exp, a):
        participant = a.participant()
        exp.handle_connect({'player_id': participant.id})
        exp.send(
            'griduniverse_ctrl:'
            '{{"type":"move","player_id":{},"move":"left"}}'.format(participant.id)
        )
        time.sleep(10)
        data = exp.retrieve_data()
        results = json.loads(exp.analyze(data))
        assert results[u'average_score'] >= 0.0
        assert results[u'average_payoff'] >= 0.0


@pytest.mark.usefixtures('env')
class TestChat(object):

    def test_appends_to_chat_history(self, exp, a):
        participant = a.participant()
        exp.handle_connect({'player_id': participant.id})

        exp.send(
            'griduniverse_ctrl:'
            '{{"type":"chat","player_id":{},"contents":"hello!"}}'.format(participant.id)
        )

        history = exp.grid.chat_message_history
        assert len(history) == 1
        assert 'hello!' in history[0]

    def test_republishes_non_broadcasts(self, exp, a, pubsub):
        participant = a.participant()
        exp.handle_connect({'player_id': participant.id})

        exp.send(
            'griduniverse_ctrl:'
            '{{"type":"chat","player_id":{},"contents":"hello!"}}'.format(participant.id)
        )

        pubsub.publish.assert_called()

    def test_does_not_republish_broadcasts(self, exp, a, pubsub):
        participant = a.participant()
        exp.handle_connect({'player_id': participant.id})

        exp.send(
            'griduniverse_ctrl:'
            '{{"type":"chat","player_id":{},"contents":"hello!","broadcast":"true"}}'.format(
                participant.id
            )
        )

        pubsub.publish.assert_not_called()


@pytest.mark.usefixtures('env')
class TestDonation(object):

    def test_group_donations_distributed_evenly_across_team(self, exp, a):
        donor = a.participant()
        teammate = a.participant()
        exp.handle_connect({'player_id': donor.id})
        exp.handle_connect({'player_id': teammate.id})
        donor_player = exp.grid.players[1]
        teammate_player = exp.grid.players[2]
        # put them on the same team:
        exp.handle_change_color(
            {
                'player_id': teammate_player.id,
                'color': donor_player.color
            }
        )
        # make donation active
        exp.grid.donation_group = True
        exp.grid.donation_amount = 1
        donor_player.score = 2

        exp.handle_donation(
            {
                'donor_id': donor_player.id,
                'recipient_id': 'group:{}'.format(donor_player.color_idx),
                'amount': 2
            }
        )
        assert donor_player.score == 1
        assert teammate_player.score == 1

    def test_public_donations_distributed_evenly_across_players(self, exp, a):
        donor = a.participant()
        opponent = a.participant()
        exp.handle_connect({'player_id': donor.id})
        exp.handle_connect({'player_id': opponent.id})
        donor_player = exp.grid.players[1]
        opponent_player = exp.grid.players[2]
        exp.grid.donation_public = True
        exp.grid.donation_amount = 1
        donor_player.score = 2

        exp.handle_donation(
            {
                'donor_id': donor_player.id,
                'recipient_id': 'all',
                'amount': 2
            }
        )

        assert donor_player.score == 1
        assert opponent_player.score == 1
