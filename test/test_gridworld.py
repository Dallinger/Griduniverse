import mock
import pytest


@pytest.mark.usefixtures('env')
class TestFoodSupply(object):

    def test_spawn_item_at_position(self, gridworld):
        # reset food state
        gridworld.items_updated = False
        assert len(gridworld.item_locations.keys()) == 0
        assert gridworld.item_locations.get((0, 0)) is None
        # Spawn food at specific location
        gridworld.spawn_item(position=(0, 0))
        assert gridworld.items_updated is True
        assert gridworld.item_locations.get((0, 0)) is not None

    def test_spawn_item_at_random(self, gridworld):
        # reset food state
        gridworld.items_updated = False
        assert len(gridworld.item_locations.keys()) == 0
        # Spawn food at random location with no arguments
        gridworld.spawn_item()
        assert gridworld.items_updated is True
        assert len(gridworld.item_locations.keys()) == 1


@pytest.mark.usefixtures('env')
class TestSerialize(object):

    def test_serializes_players(self, gridworld):
        player = mock.Mock()
        player.serialize.return_value = 'Serialized Player'
        gridworld.players = {1: player}
        values = gridworld.serialize()
        assert values['players'] == ['Serialized Player']
        assert values['round'] == 0
        assert values['donation_active'] == gridworld.donation_active
        assert values['rows'] == gridworld.rows
        assert values['columns'] == gridworld.columns

    def test_serializes_items_and_walls(self, gridworld):
        values = gridworld.serialize()
        assert values.get('walls') == []
        assert values.get('items') == []
        wall = mock.Mock()
        items = mock.Mock()
        wall.serialize.return_value = 'Serialized Wall'
        items.serialize.return_value = 'Serialized Item'
        gridworld.wall_locations[(1, 1)] = wall
        gridworld.item_locations[(2, 2)] = items
        values = gridworld.serialize()
        assert values.get('walls') == ['Serialized Wall']
        assert values.get('items') == ['Serialized Item']

    def test_food_and_wall_serialization_disabled(self, gridworld):
        gridworld.wall_locations[(1, 1)] = 'ignored'
        gridworld.item_locations[(2, 2)] = 'ignored'
        values = gridworld.serialize(include_walls=False, include_items=False)
        assert values.get('walls') is None
        assert values.get('food') is None


@pytest.mark.usefixtures('env')
class TestRoundState(object):

    def test_check_round_not_started(self, gridworld):
        # Game hasn't started
        gridworld._start_if_ready()
        gridworld.check_round_completion()
        assert gridworld.round == 0
        assert gridworld.start_timestamp is None
        assert gridworld.remaining_round_time == 0
        assert gridworld.game_over is False

    def test_check_round_starts_with_players(self, gridworld):
        # Adding players starts the game
        gridworld.players = {1: mock.Mock()}
        gridworld._start_if_ready()
        gridworld.check_round_completion()
        assert gridworld.start_timestamp is not None
        assert round(gridworld.remaining_round_time) == round(gridworld.time_per_round)
        assert gridworld.round == 0

    def test_check_round_change(self, gridworld):
        gridworld.players = {1: mock.Mock()}
        gridworld.num_rounds = 2
        gridworld._start_if_ready()
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

    def test_game_end(self, gridworld):
        gridworld.players = {1: mock.Mock()}
        gridworld.num_rounds = 1
        gridworld._start_if_ready()
        with mock.patch('time.time') as mod_time:
            # Finish final round
            start_time = gridworld.start_timestamp
            mod_time.return_value = start_time + gridworld.time_per_round
            gridworld.check_round_completion()
            assert gridworld.remaining_round_time == 0
            assert gridworld.game_over is True


@pytest.mark.usefixtures('env')
class TestInstructions(object):

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
