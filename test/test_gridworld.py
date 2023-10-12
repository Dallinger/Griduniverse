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

    def test_replenish_items_boosts_item_count_to_target(self, gridworld):
        target = sum(item.get("item_count") for item in gridworld.item_config.values())

        gridworld.replenish_items()

        target == len(gridworld.item_locations)


@pytest.mark.usefixtures("env")
class TestSerialize(object):
    def test_serializes_players(self, gridworld):
        player = mock.Mock()
        player.serialize.return_value = "Serialized Player"
        gridworld.players = {1: player}

        values = gridworld.serialize()

        assert values["players"] == ["Serialized Player"]

    def test_serializes_game_state(self, gridworld):
        values = gridworld.serialize()

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


class TestDeserialize(object):
    def test_round_trip(self, gridworld):
        # Walls ("classic")
        gridworld.walls_density = 0.0001
        gridworld.build_labyrinth()
        # Items
        gridworld.replenish_items()
        # Players
        gridworld.spawn_player(1)
        gridworld.spawn_player(2)

        # Save state, so we can verify that we restore all the same values
        saved = gridworld.serialize()

        # Clear everything, so we can verify it's restored via
        # deserialization:
        gridworld.wall_locations.clear()
        gridworld.item_locations.clear()
        gridworld.players.clear()
        gridworld.round = None

        gridworld.deserialize(saved)

        refetched = gridworld.serialize()

        assert saved == refetched


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
        assert "🫐 Gooseberry (3 points)" in html


class TestMatrix2SerializedGridworld(object):
    """Tests for converting a list of lists extracted from matrix
    representation of initial grid state into the format used in
    Gridworld [de]serialization.
    """

    @property
    def subject(self):
        from dlgr.griduniverse.csv_gridworlds import matrix2gridworld

        return matrix2gridworld

    def test_transformation_one_row(self):
        csv = [["w", "stone", "", "gooseberry_bush|3", "p1c2"]]

        result = self.subject(csv)

        assert result == {
            "columns": 5,
            "rows": 1,
            "items": [
                {
                    "item_id": "stone",
                    "position": [1, 0],
                },
                {
                    "item_id": "gooseberry_bush",
                    "position": [3, 0],
                    "remaining_uses": 3,
                },
            ],
            "walls": [
                [0, 0],
            ],
            "players": [
                {
                    "color": "YELLOW",
                    "position": [4, 0],
                    "id": 1,
                }
            ],
        }

    def test_transformation_multirow(self):
        csv = [
            ["w", "stone", "", "gooseberry_bush|3", "p1c1"],
            ["", "w", "", "", ""],
            ["", "p2c1", "w", "", ""],
            ["", "", "", "w", ""],
            ["", "", "", "p3c2", "w"],
            ["", "", "", "", "w"],
            ["gooseberry_bush|4", "", "", "", ""],
            ["", "big_hard_rock", "", "", ""],
            ["", "p4c2", "", "", ""],
            ["", "", "p5c3", "", ""],
        ]

        result = self.subject(csv)

        assert result == {
            "columns": 5,
            "rows": 10,
            "items": [
                {
                    "item_id": "stone",
                    "position": [1, 0],
                },
                {
                    "item_id": "gooseberry_bush",
                    "position": [3, 0],
                    "remaining_uses": 3,
                },
                {
                    "item_id": "gooseberry_bush",
                    "position": [0, 6],
                    "remaining_uses": 4,
                },
                {
                    "item_id": "big_hard_rock",
                    "position": [1, 7],
                },
            ],
            "walls": [
                [0, 0],
                [1, 1],
                [2, 2],
                [3, 3],
                [4, 4],
                [4, 5],
            ],
            "players": [
                {
                    "color": "BLUE",
                    "position": [4, 0],
                    "id": 1,
                },
                {
                    "color": "BLUE",
                    "position": [1, 2],
                    "id": 2,
                },
                {
                    "color": "YELLOW",
                    "position": [3, 4],
                    "id": 3,
                },
                {
                    "color": "YELLOW",
                    "position": [1, 8],
                    "id": 4,
                },
                {
                    "color": "ORANGE",
                    "position": [2, 9],
                    "id": 5,
                },
            ],
        }

    def test_transformation_empty_matrix(self):
        csv = []

        result = self.subject(csv)

        assert result == {"rows": 0, "columns": 0}

    def test_transformation_not_confused_by_whitepace(self):
        csv = [["w ", "  stone", "  ", " gooseberry_bush | 3 ", " p1c2"]]

        result = self.subject(csv)

        assert result == {
            "columns": 5,
            "rows": 1,
            "items": [
                {
                    "item_id": "stone",
                    "position": [1, 0],
                },
                {
                    "item_id": "gooseberry_bush",
                    "position": [3, 0],
                    "remaining_uses": 3,
                },
            ],
            "walls": [
                [0, 0],
            ],
            "players": [
                {
                    "color": "YELLOW",
                    "position": [4, 0],
                    "id": 1,
                }
            ],
        }

    def test_transformation_explains_invalid_player_colors(self):
        csv = [["p1c999"]]

        with pytest.raises(ValueError) as exc_info:
            self.subject(csv)

        assert exc_info.match("Invalid player color")
