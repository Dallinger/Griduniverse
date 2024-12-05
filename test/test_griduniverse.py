"""
Tests for `dlgr.griduniverse` module.
"""
import collections
import json
import time

import mock
import pytest

from dlgr.griduniverse.experiment import Player


class TestDependenciesLoaded(object):
    def test_faker_importable(self):
        import faker

        assert faker is not None


class TestItem(object):
    @pytest.fixture
    def item_config(self):
        return {
            "item_id": 9,
            "calories": 5,
            "crossable": True,
            "interactive": False,
            "maturation_speed": 1,
            "maturation_threshold": 0.0,
            "n_uses": 3,
            "name": "Food",
            "plantable": False,
            "planting_cost": 1,
            "portable": True,
            "spawn_rate": 0.1,
            "sprite": "#8a9b0f,#7a6b54",
        }

    @property
    def subject(self):
        from dlgr.griduniverse.experiment import Item

        return Item

    def test_initialized_with_some_default_values(self, item_config):
        item = self.subject(item_config)

        assert isinstance(item.creation_timestamp, float)
        assert isinstance(item.id, int)
        assert item.position == (0, 0)

    def test_instance_specific_values_can_be_specified(self, item_config):
        item = self.subject(
            item_config, id=42, position=(2, 4), creation_timestamp=21.2
        )

        assert item.id == 42
        assert item.position == (2, 4)
        assert item.creation_timestamp == 21.2

    def test_repr(self, item_config):
        item = self.subject(
            item_config, id=42, position=(2, 4), creation_timestamp=21.2
        )

        assert (
            item.__repr__()
            == "Item(name='Food', item_id=9, id=42, position=(2, 4), creation_timestamp=21.2)"
        )

    def test_inherits_shared_type_properties_from_config(self, item_config):
        item = self.subject(item_config)
        assert item.item_id == item_config["item_id"]
        assert item.name == "Food"
        assert item.calories == 5

    def test_type_properties_stored_by_reference(self, item_config):
        item = self.subject(item_config)

        assert item.calories == 5
        # Update shared type definition:
        item_config["calories"] = 6
        # Change seen in instance:
        assert item.calories == 6

    def test_type_properties_cannot_by_shadowed(self, item_config):
        item = self.subject(item_config)

        assert item.calories == 5

        with pytest.raises(TypeError):
            item.calories = 6

    def test_remaining_uses_default(self, item_config):
        item = self.subject(item_config)

        assert item.remaining_uses == item_config["n_uses"]

    def test_remaining_uses_in_constructor(self, item_config):
        item = self.subject(item_config, remaining_uses=1)

        assert item.remaining_uses == 1


@pytest.mark.usefixtures("env")
class TestExperimentClass(object):
    def test_initialization(self, exp):
        from dallinger.experiment import Experiment

        assert isinstance(exp, Experiment)

    def test_recruiter_property_is_some_subclass_of_recruiter(self, exp):
        from dallinger.recruiters import Recruiter

        assert isinstance(exp.recruiter, Recruiter)

    def test_new_experiment_has_game(self, exp):
        from dlgr.griduniverse.experiment import Game

        assert len(exp.games_by_control_channel_id) > 0
        for game in exp.games_by_control_channel_id.values():
            assert isinstance(game, Game)

    def test_new_game_has_a_grid(self, exp):
        from dlgr.griduniverse.experiment import Gridworld

        for game in exp.games_by_control_channel_id.values():
            assert isinstance(game.grid, Gridworld)

    def test_new_experiment_has_item_config_with_defaults(self, exp):
        item_config = exp.item_config
        assert isinstance(item_config, dict)
        # We define a Food item, and pull the null public good multiplier from the default
        assert item_config["stone"]["name"] == "Stone"
        assert item_config["stone"]["public_good_multiplier"] == 0.0

    def test_new_experiment_has_transition_config_with_defaults(self, exp):
        transition_config = exp.transition_config
        assert isinstance(transition_config, dict)
        for key, transition in transition_config.items():
            # We are keyed on tuples of item ids (actor, target)
            assert isinstance(key, tuple)
            assert len(key) == 2
            # ints or strings both supported for IDs
            assert isinstance(key[0], (int, str))
            assert isinstance(key[1], (int, str))
            # This value comes from the defaults
            assert transition["visible"] in {"always", "never", "seen"}
            break

    def test_create_network_builds_default_network_type(self, exp):
        from dallinger.networks import FullyConnected

        net = exp.create_network()
        assert isinstance(net, FullyConnected)

    def test_session_is_dallinger_global(self, exp, db_session):
        assert exp.session() is db_session()

    def test_recruit_does_not_raise(self, exp):
        exp.recruit()

    def test_bonus(self, participants, exp):
        # With no experiment state, bonus returns 0
        assert exp.bonus(participants[0]) == 0.0

        with mock.patch(
            "dlgr.griduniverse.experiment.Griduniverse._last_state_for_player"
        ) as state:
            state.return_value = {"id": "1", "payoff": 100.0}
            assert exp.bonus(participants[0]) == 100.0


@pytest.mark.usefixtures("env")
class TestPlayerConnects(object):
    def test_handle_connect_creates_node(self, exp, game, a):
        participant = a.participant()
        exp.handle_connect({"player_id": participant.id})
        assert participant.id in game.node_by_player_id

    def test_handle_connect_adds_player_to_grid(self, exp, game, a):
        participant = a.participant()
        exp.handle_connect({"player_id": participant.id})
        assert participant.id in game.grid.players

    def test_handle_connect_uses_existing_player_on_grid(self, exp, game, a):
        participant = a.participant()
        game.grid.players[participant.id] = Player(
            id=participant.id, color=[0.50, 0.86, 1.00], location=[10, 10]
        )
        exp.handle_connect({"player_id": participant.id})
        assert participant.id in game.node_by_player_id
        assert len(game.grid.players) == 1
        assert len(game.node_by_player_id) == 1

    def test_handle_connect_is_noop_for_spectators(self, exp, game):
        exp.handle_connect({"player_id": "spectator"})
        assert game.node_by_player_id == {}

    def test_colors_distributed_evenly(self, exp, game, participants):
        game.grid.num_players = 9
        exp.networks()[0].max_size = 10
        players = [
            exp.handle_connect({"player_id": participant.id})
            or game.grid.players[participant.id]
            for participant in participants[:9]
        ]
        colors = collections.Counter([player.color_idx for player in players])
        # All colors are assigned to 3 players
        assert set(colors.values()) == {3}

    def test_colors_distributed_almost_evenly_if_on_edge(self, exp, game, participants):
        exp.num_colors = 2
        game.grid.num_players = 9
        exp.networks()[0].max_size = 10
        players = [
            exp.handle_connect({"player_id": participant.id})
            or game.grid.players[participant.id]
            for participant in participants[:9]
        ]
        colors = collections.Counter([player.color_idx for player in players])
        # One color is assigned to 4 players and the other is assigned to 5
        assert set(colors.values()) == {4, 5}


@pytest.mark.usefixtures("env")
class TestRecordPlayerActivity(object):
    def test_records_player_events(self, exp, a):
        participant = a.participant()
        exp.handle_connect({"player_id": participant.id})
        exp.send(
            "griduniverse_ctrl-1:"
            '{{"type":"move","player_id":{},"move":"left"}}'.format(participant.id)
        )
        time.sleep(10)
        data = exp.retrieve_data()
        # Get the last recorded event
        event_detail = json.loads(data.infos.df["details"].values[-1])
        assert event_detail["player_id"] == participant.id
        assert event_detail["move"] == "left"

    def test_scores_and_payoffs_averaged(self, exp, a):
        participant = a.participant()
        exp.handle_connect({"player_id": participant.id})
        exp.send(
            "griduniverse_ctrl-1:"
            '{{"type":"move","player_id":{},"move":"left"}}'.format(participant.id)
        )
        time.sleep(10)
        data = exp.retrieve_data()
        results = json.loads(exp.analyze(data))
        assert results["average_score"] >= 0.0
        assert results["average_payoff"] >= 0.0


@pytest.mark.usefixtures("env")
class TestChat(object):
    def test_republishes_non_broadcasts(self, exp, a, pubsub):
        participant = a.participant()
        exp.handle_connect({"player_id": participant.id})

        exp.send(
            "griduniverse_ctrl-1:"
            '{{"type":"chat","player_id":{},"contents":"hello!"}}'.format(
                participant.id
            )
        )

        pubsub.publish.assert_called()

    def test_does_not_republish_broadcasts(self, exp, a, pubsub):
        participant = a.participant()
        exp.handle_connect({"player_id": participant.id})

        exp.send(
            "griduniverse_ctrl-1:"
            '{{"type":"chat","player_id":{},"contents":"hello!","broadcast":"true"}}'.format(
                participant.id
            )
        )

        pubsub.publish.assert_not_called()


@pytest.mark.usefixtures("env")
class TestInstructions(object):
    def test_instructions(self, exp):
        # Just test something basic
        html = exp.instructions()
        assert "🫐 Gooseberry (3 points)" in html
