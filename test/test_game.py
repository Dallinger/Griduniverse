import csv
import time

import mock
import pytest

from dlgr.griduniverse.experiment import Player


@pytest.mark.usefixtures("env", "fake_gsleep")
class TestGameLoops(object):
    @pytest.fixture
    def loop_game_3x(self, game):
        game.grid.start_timestamp = time.time()
        game.socket_session = mock.Mock()
        game.publish = mock.Mock()

        def count_down(counter):
            for c in counter:
                return False
            return True

        end_counter = (i for i in range(3))
        start_counter = (i for i in range(3))

        with mock.patch(
            "dlgr.griduniverse.experiment.Gridworld.game_started",
            new_callable=mock.PropertyMock,
        ) as started:
            with mock.patch(
                "dlgr.griduniverse.experiment.Gridworld.game_over",
                new_callable=mock.PropertyMock,
            ) as over:
                started.side_effect = lambda: count_down(start_counter)
                over.side_effect = lambda: count_down(end_counter)

                yield game

    def test_socket_session_is_not_dallinger_global(self, game, db_session):
        # Experiment creates socket_session
        assert game.socket_session() is not db_session()

    def test_loop_builds_labrynth(self, loop_game_3x):
        game = loop_game_3x
        game.grid.walls_density = 0.01

        game.game_loop()

        state = game.grid.serialize()
        assert len(state["walls"]) > 1

    def test_loop_spawns_items(self, loop_game_3x):
        game = loop_game_3x
        game.game_loop()

        state = game.grid.serialize()
        assert len(state["items"]) == sum(
            [i["item_count"] for i in game.item_config.values()]
        )

    def test_builds_grid_from_csv_if_specified(self, tmpdir, loop_game_3x):
        game = loop_game_3x
        grid_config = [["w", "stone", "", "gooseberry_bush|3", "p1c2"]]
        # Grid size must match incoming data, so update the gridworlds's existing
        # settings:
        game.grid.rows = len(grid_config)
        game.grid.columns = len(grid_config[0])

        csv_file = tmpdir.join("test_grid.csv")

        with csv_file.open(mode="w") as file:
            writer = csv.writer(file)
            writer.writerows(grid_config)

        # active_config.extend({"map_csv": csv_file.strpath}, strict=True)
        game.config["map_csv"] = csv_file.strpath

        game.game_loop()

        state = game.grid.serialize()

        def relevant_keys(dictionary):
            relevant = {"id", "item_id", "position", "remaining_uses", "color"}
            return {k: v for k, v in dictionary.items() if k in relevant}

        # Ignore keys added by experiment execution we don't care about and/or
        # which are non-deterministic (like player names):
        state["items"] = [relevant_keys(item) for item in state["items"]]
        state["players"] = [relevant_keys(player) for player in state["players"]]

        assert state == {
            "columns": 5,
            "donation_active": False,
            "items": [
                {
                    "id": 1,
                    "item_id": "stone",
                    "position": [0, 1],
                    "remaining_uses": 1,
                },
                {
                    "id": 2,
                    "item_id": "gooseberry_bush",
                    "position": [0, 3],
                    "remaining_uses": 3,
                },
            ],
            "players": [
                {
                    "color": "YELLOW",
                    "id": "1",
                    "position": [0, 4],
                }
            ],
            "round": 0,
            "rows": 1,
            "walls": [[0, 0]],
        }

    def test_loop_serialized_and_saves(self, loop_game_3x):
        # Grid serialized and added to DB session once per loop
        game = loop_game_3x
        game.game_loop()

        assert game.socket_session.add.call_count == 3
        # Session commited once per loop and again at end
        assert game.socket_session.commit.call_count == 4

    def test_loop_resets_state(self, loop_game_3x):
        # Wall and item state unset, item count reset during loop
        game = loop_game_3x
        game.game_loop()
        assert game.grid.walls_updated is False
        assert game.grid.items_updated is False

    def test_loop_taxes_points(self, loop_game_3x):
        # Player is taxed one point during the timed event round
        game = loop_game_3x
        game.grid.tax = 1.0
        game.grid.players = {"1": Player(id="1", score=10.0)}

        # Ensure one timed events round
        game.grid.start_timestamp -= 2

        game.game_loop()
        assert game.grid.players["1"].score == 9.0

    def test_loop_computes_payoffs(self, loop_game_3x):
        # Payoffs computed once per loop before checking round completion
        game = loop_game_3x
        game.grid.dollars_per_point = 0.5
        game.grid.players = {"1": Player(id="1", score=10.0)}

        game.game_loop()

        assert game.grid.players["1"].payoff == 5.0

    def test_loop_publishes_stop_event(self, loop_game_3x):
        # publish called with stop event at end of round
        game = loop_game_3x
        game.game_loop()
        game.publish.assert_called_once_with({"type": "stop"})

    def test_send_state_thread(self, loop_game_3x):
        game = loop_game_3x
        # The game state thread only starts when it has enough players
        game.grid.players = {
            "1": Player(id="1", score=0.0),
            "2": Player(id="1", score=0.0),
            "3": Player(id="3", score=0.0),
        }
        game.send_state_thread()

        # State thread will loop 4 times before the loop is broken,
        # and publish called with grid state message once per loop
        assert game.publish.call_count == 4

    def test_environment_uses_game_network(self, game, exp):
        assert game.environment.network.id in {n.id for n in exp.networks()}
        assert game.environment.network.id == game.network_id


@pytest.mark.usefixtures("env")
class TestRecordPlayerGameActivity(object):
    def test_record_event_with_participant(self, exp, game, a):
        # Adds event to player node
        participant = a.participant()
        exp.handle_connect({"player_id": participant.id})
        game.socket_session.add = mock.Mock()
        game.socket_session.commit = mock.Mock()
        game.record_event({"data": ["some data"]}, player_id=participant.id)
        game.socket_session.add.assert_called_once()
        game.socket_session.commit.assert_called_once()
        info = game.socket_session.add.call_args[0][0]
        assert info.details["data"] == ["some data"]
        assert info.origin.id == game.node_by_player_id[participant.id]

    def test_record_event_without_participant(self, game):
        # Adds event to enviroment node
        node = game.environment
        game.socket_session.add = mock.Mock()
        game.socket_session.commit = mock.Mock()
        game.record_event({"data": ["some data"]})
        game.socket_session.add.assert_called_once()
        game.socket_session.commit.assert_called_once()
        info = game.socket_session.add.call_args[0][0]
        assert info.details["data"] == ["some data"]
        assert info.origin.id == node.id

    def test_record_event_with_failed_node(self, game, a):
        # Does not save event, but logs failure
        node = game.environment
        node.failed = True
        game.socket_session.add = mock.Mock()
        game.socket_session.commit = mock.Mock()
        with mock.patch("dlgr.griduniverse.experiment.logger.info") as logger:
            game.record_event({"data": ["some data"]})
            assert game.socket_session.add.call_count == 0
            assert game.socket_session.commit.call_count == 0
            logger.assert_called_once()
            assert logger.call_args.startswith(
                "Tried to record an event after node#{} failure:".format(node.id)
            )


@pytest.mark.usefixtures("env")
class TestGameChat(object):
    def test_appends_to_chat_history(self, exp, game, a):
        participant = a.participant()
        exp.handle_connect({"player_id": participant.id})

        exp.send(
            "griduniverse_ctrl-1:"
            '{{"type":"chat","player_id":{},"contents":"hello!"}}'.format(
                participant.id
            )
        )

        history = game.grid.chat_message_history
        assert len(history) == 1
        assert "hello!" in history[0]

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
class TestDonation(object):
    def test_group_donations_distributed_evenly_across_team(self, exp, game, a):
        donor = a.participant()
        teammate = a.participant()
        exp.handle_connect({"player_id": donor.id})
        exp.handle_connect({"player_id": teammate.id})
        donor_player = game.grid.players[1]
        teammate_player = game.grid.players[2]
        # put them on the same team:
        game.handle_change_color(
            {"player_id": teammate_player.id, "color": donor_player.color}
        )
        # make donation active
        game.grid.donation_group = True
        game.grid.donation_amount = 1
        donor_player.score = 2

        game.handle_donation(
            {
                "donor_id": donor_player.id,
                "recipient_id": "group:{}".format(donor_player.color_idx),
                "amount": 2,
            }
        )
        assert donor_player.score == 1
        assert teammate_player.score == 1

    def test_public_donations_distributed_evenly_across_players(self, exp, game, a):
        donor = a.participant()
        opponent = a.participant()
        exp.handle_connect({"player_id": donor.id})
        exp.handle_connect({"player_id": opponent.id})
        donor_player = game.grid.players[1]
        opponent_player = game.grid.players[2]
        game.grid.donation_public = True
        game.grid.donation_amount = 1
        donor_player.score = 2

        game.handle_donation(
            {"donor_id": donor_player.id, "recipient_id": "all", "amount": 2}
        )

        assert donor_player.score == 1
        assert opponent_player.score == 1
