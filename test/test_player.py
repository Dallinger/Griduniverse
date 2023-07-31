import pytest
from dlgr.griduniverse.experiment import Player


class TestInstantiation(object):
    def test_has_sensible_defaults(self):
        from dlgr.griduniverse.experiment import Gridworld

        player = Player()
        assert player.position == [0, 0]
        assert not player.motion_auto
        assert player.score == 0
        assert player.motion_tremble_rate == 0
        assert player.color in Gridworld.player_color_names

    def test_has_a_persona(self):
        player = Player()
        assert hasattr(player, "name")
        assert player.gender in ("F", "M")

    def test_can_assign_color_by_name(self):
        player = Player(color_name="BLUE")
        assert player.color == "BLUE"


class TestIsAwareOfOtherPlayersOnGrid(object):
    def test_knows_if_its_adjacent_to_another_player(self):
        player = Player()
        assert player.is_neighbor(Player(position=[0, 1]))
        assert not player.is_neighbor(Player(position=[0, 2]))

    def test_diagonally_adjacent_does_not_count_as_neighbor(self):
        player = Player()
        assert not player.is_neighbor(Player(position=[1, 1]))

    def test_has_no_neighbors_by_default(self):
        player = Player()
        assert player.neighbors() == []

    def test_can_find_neighbors_via_the_grid(self, gridworld):
        player1 = gridworld.spawn_player("1")
        player2 = gridworld.spawn_player("2")

        player1.position = [0, 0]
        player2.position = [0, 1]

        assert player2 in player1.neighbors()


class TestMovement(object):
    """Note: writing these tests deepened my suspicion that movement should
    be managed by the Gridworld (or a new, smaller object) rather than Player.
    JMS 10/5/2018
    """

    def test_needs_a_grid_for_context(self):
        player = Player()
        with pytest.raises(AttributeError):
            player.move("right")

    def test_can_move_into_empty_location_immediately_if_no_speed_limit(
        self, gridworld
    ):
        player = gridworld.spawn_player("1")
        player.position = [0, 0]
        player.motion_speed_limit = 0

        player.move("right")

        assert player.position == [0, 1]

    def test_successful_move_returns_direction_in_message(self, gridworld):
        player = gridworld.spawn_player("1")
        player.position = [0, 0]
        player.motion_speed_limit = 0

        message = player.move("right")

        assert message["direction"] == "right"

    def test_can_add_wall_on_move(self, gridworld):
        player = gridworld.spawn_player("1")
        player.position = [0, 0]
        player.add_wall = [0, 0]
        player.motion_speed_limit = 0

        message = player.move("right")

        assert message["direction"] == "right"
        assert message["wall"] == {"type": "wall_built", "wall": [0, 0]}
        assert gridworld.has_wall([0, 0])

    def test_cannot_move_immediately_if_speed_limit_enforced(self, gridworld):
        from dlgr.griduniverse.experiment import IllegalMove

        player = gridworld.spawn_player("1")
        player.position = [0, 0]

        with pytest.raises(IllegalMove) as ex_info:
            player.move("right")
            assert ex_info.match("wait time has not passed")

        assert player.position == [0, 0]

    def test_cannot_move_if_motion_has_cost_exceeding_score(self, gridworld):
        from dlgr.griduniverse.experiment import IllegalMove

        player = gridworld.spawn_player("1")
        player.motion_speed_limit = 0
        player.motion_cost = 1
        player.position = [0, 0]

        with pytest.raises(IllegalMove) as ex_info:
            player.move("right")
            assert ex_info.match("Not enough points")

        assert player.position == [0, 0]

    def test_cannot_move_if_space_is_occupied(self, gridworld):
        from dlgr.griduniverse.experiment import IllegalMove

        player = gridworld.spawn_player("1")
        occupier = gridworld.spawn_player("2")
        occupier.position = [0, 1]
        player.motion_speed_limit = 0
        player.position = [0, 0]

        with pytest.raises(IllegalMove) as ex_info:
            player.move("right")
            assert ex_info.match("not open")

        assert player.position == [0, 0]

    def test_tremble_sends_player_in_another_direction(self):
        player = Player()
        assert player.tremble("up") in ("down", "left", "right")
