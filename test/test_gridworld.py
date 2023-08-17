import mock
import pytest


@pytest.mark.usefixtures("env")
class TestItemSpawning(object):
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


@pytest.mark.usefixtures("env")
class TestSerialize(object):
    def test_serializes_players(self, gridworld):
        player = mock.Mock()
        player.serialize.return_value = "Serialized Player"
        gridworld.players = {1: player}
        values = gridworld.serialize()
        assert values["players"] == ["Serialized Player"]
        assert values["round"] == 0
        assert values["donation_active"] == gridworld.donation_active
        assert values["rows"] == gridworld.rows
        assert values["columns"] == gridworld.columns

    def test_serializes_items_and_walls(self, gridworld):
        values = gridworld.serialize()
        assert values.get("walls") == []
        assert values.get("items") == []
        wall = mock.Mock()
        items = mock.Mock()
        wall.serialize.return_value = "Serialized Wall"
        items.serialize.return_value = "Serialized Item"
        gridworld.wall_locations[(1, 1)] = wall
        gridworld.item_locations[(2, 2)] = items
        values = gridworld.serialize()
        assert values.get("walls") == ["Serialized Wall"]
        assert values.get("items") == ["Serialized Item"]

    def test_food_and_wall_serialization_disabled(self, gridworld):
        gridworld.wall_locations[(1, 1)] = "ignored"
        gridworld.item_locations[(2, 2)] = "ignored"
        values = gridworld.serialize(include_walls=False, include_items=False)
        assert values.get("walls") is None
        assert values.get("food") is None


@pytest.mark.usefixtures("env")
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
        with mock.patch("time.time") as mod_time:
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
        with mock.patch("time.time") as mod_time:
            # Finish final round
            start_time = gridworld.start_timestamp
            mod_time.return_value = start_time + gridworld.time_per_round
            gridworld.check_round_completion()
            assert gridworld.remaining_round_time == 0
            assert gridworld.game_over is True


@pytest.mark.usefixtures("env")
class TestInstructions(object):
    def test_instructions(self, gridworld):
        # Just test something basic
        html = gridworld.instructions()
        assert f"🫐 Gooseberry (3 points)" in html
