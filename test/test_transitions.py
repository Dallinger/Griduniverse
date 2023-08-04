import pytest


class TestPickupDrop(object):
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

    def test_pickup_item_success(self, item, exp, participant):
        exp.handle_item_pick_up(msg={"player_id": participant.id, "position": (0, 0)})
        assert not exp.grid.item_locations  # The item is no longer there
        assert participant.current_item == item  # The item is now in the player's inventory

    def test_pickup_item_full_hands_error(self, item, mocked_exp, participant):
        participant.current_item = self.create_item()

        mocked_exp.handle_item_pick_up(msg={"player_id": participant.id, "position": (0, 0)})
        assert list(mocked_exp.grid.item_locations.keys()) == [(0, 0)]  # The item is still there
        assert participant.current_item != item  # The item is not in the player's inventory
        assert len(self.messages) == 1

    def test_pickup_item_no_item_error(self, item, mocked_exp, participant):
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


class TestHandleItemTransition(object):
    messages = []

    @pytest.fixture(scope="function")
    def mocked_exp(self, exp):
        def publish(error_msg):
            self.messages.append(error_msg)
        exp.publish = publish
        exp.transition_config = {
            ('last', 2, 3): {
                'actor_end': 5,
                'actor_start': 2,
                'last_use': False,
                'modify_uses': [0, 0],
                'target_end': 3,
                'target_start': 3,
                'visible': 'always'
            },
        }
        yield exp
        self.messages[:] = []

    @pytest.fixture
    def item(self, exp):
        item = self.create_item()
        exp.grid.item_locations[(0, 0)] = item
        return item

    @pytest.fixture
    def participant(self, exp, a):
        participant = a.participant()
        participant.current_item = None
        exp.grid.players[participant.id] = participant
        return participant

    def create_item(self, **kwargs):
        from dlgr.griduniverse.experiment import Item

        item_data = {
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
        }
        item_data.update(kwargs)
        return Item(item_data)

    def test_handle_item_transition_combine_items(self, mocked_exp, participant):
        big_hard_rock = self.create_item(**mocked_exp.item_config[3])
        stone = self.create_item(**mocked_exp.item_config[2])
        assert stone.name == "Stone"
        assert big_hard_rock.name == "Big Hard Rock"
        mocked_exp.grid.item_locations[(0, 0)] = big_hard_rock
        participant.current_item = stone
        mocked_exp.handle_item_transition(msg={"player_id": participant.id, "position": (0, 0)})
        # The Sone has been consumed, and a Sharp Stone has been created.
        # The Big Hard Rock is still there.
        assert participant.current_item.name == "Sharp Stone"
        assert len(mocked_exp.grid.items_consumed) == 1
        assert len(mocked_exp.grid.item_locations) == 1
        list(mocked_exp.grid.item_locations.values())[0].name == "Big Hard Rock"
