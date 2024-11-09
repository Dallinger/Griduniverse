import pytest


class TestPickupDrop(object):
    messages = []

    @pytest.fixture(scope="function")
    def mocked_game(self, game):
        def publish(error_msg):
            self.messages.append(error_msg)

        game.publish = publish
        yield game
        self.messages[:] = []

    def test_pickup_item_success(self, item, game, player):
        game.handle_item_pick_up(msg={"player_id": player.id, "position": (0, 0)})
        assert not game.grid.item_locations  # The item is no longer there
        assert player.current_item == item  # The item is now in the player's inventory

    def test_pickup_item_full_hands_error(self, item, mocked_game, player):
        player.current_item = create_item()

        mocked_game.handle_item_pick_up(
            msg={"player_id": player.id, "position": (0, 0)}
        )
        assert list(mocked_game.grid.item_locations.keys()) == [
            (0, 0)
        ]  # The item is still there
        assert player.current_item != item  # The item is not in the player's inventory
        assert len(self.messages) == 1

    def test_pickup_item_no_item_error(self, item, mocked_game, player):
        mocked_game.handle_item_pick_up(
            msg={"player_id": player.id, "position": (0, 1)}
        )
        assert list(mocked_game.grid.item_locations.keys()) == [
            (0, 0)
        ]  # The item is still there
        assert player.current_item != item  # The item is not in the player's inventory
        assert len(self.messages) == 1

    def test_drop_item_success(self, game, player):
        player.current_item = item = create_item()

        game.handle_item_drop(msg={"player_id": player.id, "position": (3, 3)})
        assert list(game.grid.item_locations.keys()) == [(3, 3)]
        assert item.position == (3, 3)

    def test_drop_item_cant_drop_error(self, mocked_game, player, item):
        """The user tries to drop an item over an exiting item."""
        assert item  # The `item` fixture places it at (0, 0)
        player.current_item = create_item()  # The player has an item in their hands

        mocked_game.handle_item_drop(msg={"player_id": player.id, "position": (0, 0)})
        # Dropping failed, so the item is still in the player's hands
        assert player.current_item
        assert len(self.messages) == 1  # and we get an error message


class TestHandleItemTransition(object):
    messages = []

    @pytest.fixture(scope="function")
    def mocked_game(self, game):
        def publish(error_msg):
            self.messages.append(error_msg)

        game.publish = publish
        yield game
        self.messages[:] = []

    def test_handle_item_transition_combine_items(self, mocked_game, player):
        big_hard_rock = create_item(**mocked_game.item_config["big_hard_rock"])
        stone = create_item(**mocked_game.item_config["stone"])
        assert stone.name == "Stone"
        assert big_hard_rock.name == "Big Hard Rock"
        mocked_game.grid.item_locations[(0, 0)] = big_hard_rock
        player.current_item = stone
        mocked_game.handle_item_transition(
            msg={"player_id": player.id, "position": (0, 0)}
        )
        # The Stone has been consumed, and a Sharp Stone has been created.
        # The Big Hard Rock is still there.
        assert player.current_item.name == "Sharp Stone"
        assert len(mocked_game.grid.items_consumed) == 1
        assert len(mocked_game.grid.item_locations) == 1
        assert list(mocked_game.grid.item_locations.values())[0].name == "Big Hard Rock"

    def test_handle_item_transition_transforms_items(self, mocked_game, player):
        mocked_game.transition_config[("stone", "big_hard_rock")] = {
            "actor_start": "stone",
            "actor_end": None,
            "target_start": "big_hard_rock",
            "target_end": "sharp_stone",
            "last_use": False,
            "modify_uses": [0, 0],
            "visible": "always",
        }
        big_hard_rock = create_item(**mocked_game.item_config["big_hard_rock"])
        stone = create_item(**mocked_game.item_config["stone"])
        mocked_game.grid.item_locations[(0, 0)] = big_hard_rock
        player.current_item = stone

        mocked_game.handle_item_transition(
            msg={"player_id": player.id, "position": (0, 0)}
        )

        # The Stone and the Big Hard Rock have been transformed into a
        # Sharp Stone on the square where the Big Hard Rock was before
        assert player.current_item is None
        assert len(mocked_game.grid.items_consumed) == 2
        assert len(mocked_game.grid.item_locations) == 1
        assert list(mocked_game.grid.item_locations.values())[0].name == "Sharp Stone"

    def test_handle_item_transition_reduces_items_remaining(self, mocked_game, player):
        gooseberry_bush = create_item(**mocked_game.item_config["gooseberry_bush"])
        assert gooseberry_bush.name == "Gooseberry Bush"
        assert gooseberry_bush.remaining_uses == 6
        mocked_game.grid.item_locations[(0, 0)] = gooseberry_bush
        player.current_item = None
        mocked_game.handle_item_transition(
            msg={"player_id": player.id, "position": (0, 0)}
        )
        # The Stone has been consumed, and a Sharp Stone has been created.
        # The Big Hard Rock is still there.
        assert player.current_item.name == "Gooseberry"
        assert gooseberry_bush.remaining_uses == 5
        assert len(mocked_game.grid.items_consumed) == 0
        assert len(mocked_game.grid.item_locations) == 1
        assert (
            list(mocked_game.grid.item_locations.values())[0].name == "Gooseberry Bush"
        )

    def test_handle_last_item_transition(self, mocked_game, player):
        gooseberry_bush = create_item(**mocked_game.item_config["gooseberry_bush"])
        # Reduce the remaining uses
        gooseberry_bush.remaining_uses = 1
        assert gooseberry_bush.name == "Gooseberry Bush"
        mocked_game.grid.item_locations[(0, 0)] = gooseberry_bush
        player.current_item = None
        mocked_game.handle_item_transition(
            msg={"player_id": player.id, "position": (0, 0)}
        )
        # The Stone has been consumed, and a Sharp Stone has been created.
        # The Big Hard Rock is still there.
        assert player.current_item.name == "Gooseberry"
        assert gooseberry_bush.remaining_uses == 0
        # The bush is gone and replaced with an empty one
        assert len(mocked_game.grid.items_consumed) == 1
        assert len(mocked_game.grid.item_locations) == 1
        assert (
            list(mocked_game.grid.item_locations.values())[0].name
            == "Empty Gooseberry Bush"
        )

    def test_handle_item_transition_multiple_actors_error(self, mocked_game, player):
        stone = create_item(**mocked_game.item_config["stone"])
        mocked_game.grid.item_locations[(2, 2)] = stone
        mocked_game.grid.players[player.id].position = [2, 2]
        mocked_game.transition_config = TRANSITION_CONFIG

        mocked_game.handle_item_transition(
            msg={"player_id": player.id, "position": (2, 2)}
        )
        # Only one player was present. The transition did not happen, since it requires 2
        assert list(mocked_game.grid.item_locations.values())[0].name == "Stone"

    def test_handle_item_transition_multiple_actors_success(
        self, mocked_game, a, player
    ):
        mocked_game.transition_config = TRANSITION_CONFIG
        other_player = create_player(mocked_game, a)
        stone = create_item(**mocked_game.item_config["stone"])
        mocked_game.grid.item_locations[(2, 2)] = stone
        player.position = [2, 2]
        mocked_game.handle_item_transition(
            msg={"player_id": player.id, "position": (2, 2)}
        )
        # The second player was not close enough. The transition did not happen
        assert list(mocked_game.grid.item_locations.values())[0].name == "Stone"

        other_player.position = [2, 1]
        mocked_game.handle_item_transition(
            msg={"player_id": player.id, "position": (2, 2)}
        )
        assert list(mocked_game.grid.item_locations.values())[0].name == "Sharp Stone"

    def test_handle_item_transition_multiple_actors_distribute_calories(
        self, mocked_game, a, player
    ):
        mocked_game.transition_config = TRANSITION_CONFIG
        other_player = create_player(mocked_game, a)
        player.current_item = create_item(**mocked_game.item_config["sharp_stone"])
        stag = create_item(**mocked_game.item_config["stag"])
        mocked_game.grid.item_locations[(2, 2)] = stag
        player.position = [2, 2]
        other_player.position = [2, 1]
        mocked_game.handle_item_transition(
            msg={"player_id": player.id, "position": (2, 2)}
        )
        assert list(mocked_game.grid.item_locations.values())[0].name == "Fallen Stag"
        # The 25 total calories should be diveded evenly, but the initiator gets the reminder if any
        assert player.score == 13
        assert other_player.score == 12


class TestHandleItemConsume(object):
    messages = []

    @pytest.fixture(scope="function")
    def mocked_game(self, game):
        def publish(error_msg):
            self.messages.append(error_msg)

        game.publish = publish
        yield game
        self.messages[:] = []

    def test_consume_item(self, mocked_game, player):
        gooseberry = create_item(**mocked_game.item_config["gooseberry"])
        assert gooseberry.name == "Gooseberry"
        assert gooseberry.calories == 3
        assert getattr(player, "score", 0) == 0
        player.current_item = gooseberry
        mocked_game.handle_item_consume(
            msg={"player_id": player.id, "position": (0, 0)}
        )
        # The Gooseberry has been consumed, player score/calories increase
        assert player.current_item is None
        assert player.score == 3

    def test_consume_item_reduces_uses(self, mocked_game, player):
        gooseberry = create_item(**mocked_game.item_config["gooseberry"])
        gooseberry.remaining_uses = 4
        assert gooseberry.name == "Gooseberry"
        assert gooseberry.calories == 3
        assert getattr(player, "score", 0) == 0
        player.current_item = gooseberry
        mocked_game.handle_item_consume(
            msg={"player_id": player.id, "position": (0, 0)}
        )
        # One use of the Gooseberry has been consumed.
        assert player.current_item is gooseberry
        assert gooseberry.remaining_uses == 3
        assert player.score == 3

    def test_consume_non_consumable_sends_error(self, mocked_game, player):
        stone = create_item(**mocked_game.item_config["stone"])
        assert stone.name == "Stone"
        assert stone.calories == 0
        assert getattr(player, "score", 0) == 0
        player.current_item = stone
        mocked_game.handle_item_consume(
            msg={"player_id": player.id, "position": (0, 0)}
        )
        # stone is not consumable.
        assert player.current_item is stone
        assert getattr(player, "score", 0) == 0
        assert len(self.messages) == 1  # and we get an error message

    def test_consume_nothing_sends_error(self, mocked_game, player):
        player.current_item = None
        assert getattr(player, "score", 0) == 0
        mocked_game.handle_item_consume(
            msg={"player_id": player.id, "position": (0, 0)}
        )
        # stone is not consumable.
        assert player.current_item is None
        assert getattr(player, "score", 0) == 0
        assert len(self.messages) == 1  # and we get an error message


@pytest.fixture
def item(game):
    item = create_item()
    game.grid.item_locations[(0, 0)] = item
    return item


@pytest.fixture
def player(game, a):
    return create_player(game, a)


def create_player(game, a):
    from dlgr.griduniverse.experiment import Player

    participant = a.participant()
    player = Player(id=participant.id, grid=game.grid)
    game.grid.players[participant.id] = player
    return player


def create_item(**kwargs):
    from dlgr.griduniverse.experiment import Item

    item_data = {
        "item_id": "food",
        "calories": 5,
        "crossable": True,
        "interactive": True,
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
    item_data.update(kwargs)
    return Item(item_data)


# Configuration of transitions: tests need stable transitions,
# so we use a fixed configuration here.
TRANSITION_CONFIG = {
    ("last", None, "gooseberry_bush"): {
        "actor_end": "gooseberry",
        "actor_start": None,
        "last_use": True,
        "modify_uses": [0, -1],
        "target_end": "empty_gooseberry_bush",
        "target_start": "gooseberry_bush",
        "visible": "always",
    },
    ("sharp_stone", "wild_carrot_plant"): {
        "actor_end": "sharp_stone",
        "actor_start": "sharp_stone",
        "last_use": False,
        "modify_uses": [0, 0],
        "target_end": "wild_carrot",
        "target_start": "wild_carrot_plant",
        "visible": "seen",
    },
    (None, "gooseberry_bush"): {
        "actor_end": "gooseberry",
        "actor_start": None,
        "last_use": False,
        "modify_uses": [0, -1],
        "target_end": "gooseberry_bush",
        "target_start": "gooseberry_bush",
        "visible": "never",
    },
    (None, "stone"): {
        "actor_end": None,
        "actor_start": None,
        "last_use": False,
        "modify_uses": [0, 0],
        "required_actors": 2,
        "target_end": "sharp_stone",
        "target_start": "stone",
        "visible": "always",
    },
    ("stone", "big_hard_rock"): {
        "actor_end": "sharp_stone",
        "actor_start": "stone",
        "last_use": False,
        "modify_uses": [0, 0],
        "target_end": "big_hard_rock",
        "target_start": "big_hard_rock",
        "visible": "always",
    },
    ("sharp_stone", "stag"): {
        "actor_end": "sharp_stone",
        "actor_start": "sharp_stone",
        "last_use": False,
        "modify_uses": [0, -1],
        "required_actors": 2,
        "target_end": "fallen_stag",
        "target_start": "stag",
        "visible": "always",
        "calories": 25,
    },
}
