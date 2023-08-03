import pytest


class TestTransitions(object):
    messages = []

    @pytest.fixture(scope="function")
    def mocked_exp(self, exp):
        def publish(error_msg):
            self.messages.append(error_msg)
        exp.publish = publish
        yield exp
        self.messages[:] = []

    @pytest.fixture
    def item(self, exp):
        item = self.create_item()
        exp.grid.item_locations[(0, 0)] = item
        return item

    def create_item(self):
        from dlgr.griduniverse.experiment import Item

        return Item({
            "item_id": 9,
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
        })

    @pytest.fixture
    def participant(self, exp, a):
        participant = a.participant()
        participant.current_item = None
        exp.grid.players[participant.id] = participant
        return participant

    def test_consume_item_success(self, item, exp, participant):
        exp.handle_item_pick_up(msg={"player_id": participant.id, "position": (0, 0)})
        assert not exp.grid.item_locations  # The item is no longer there
        assert participant.current_item == item  # The item is now in the player's inventory

    def test_consume_item_full_hands_error(self, item, mocked_exp, participant):
        participant.current_item = self.create_item()

        mocked_exp.handle_item_pick_up(msg={"player_id": participant.id, "position": (0, 0)})
        assert list(mocked_exp.grid.item_locations.keys()) == [(0, 0)]  # The item is still there
        assert participant.current_item != item  # The item is not in the player's inventory
        assert len(self.messages) == 1

    def test_consume_item_no_item_error(self, item, mocked_exp, participant):
        mocked_exp.handle_item_pick_up(msg={"player_id": participant.id, "position": (0, 1)})
        assert list(mocked_exp.grid.item_locations.keys()) == [(0, 0)]  # The item is still there
        assert participant.current_item != item  # The item is not in the player's inventory
        assert len(self.messages) == 1

    def test_drop_item_success(self, exp, participant):
        participant.current_item = item = self.create_item()

        exp.handle_item_drop(msg={"player_id": participant.id, "position": (3, 3)})
        assert list(exp.grid.item_locations.keys()) == [(3, 3)]
        assert item.position == (3, 3)

    def test_drop_item_cant_drop_error(self, mocked_exp, participant, item):
        """The user tries to drop an item over an exiting item.
        """
        assert item  # The `item` fixture places it at (0, 0)
        participant.current_item = self.create_item()  # The participant has an item in their hands

        mocked_exp.handle_item_drop(msg={"player_id": participant.id, "position": (0, 0)})
        # Dropping failed, so the item is still in the player's hands
        assert participant.current_item
        assert len(self.messages) == 1  # and we get an error message
