import time

import pytest


class TestAutoTransition(object):
    messages = []

    def test_automatic_transition(self, exp):
        from dlgr.griduniverse.experiment import Item

        item = Item(
            {
                "id": 1,
                "item_id": "sunflower_sprout",
                "name": "Sunflower Sprout",
                "n_uses": 1,
            }
        )
        exp.grid.item_locations[(2, 2)] = item

        exp.grid.trigger_transitions(time=lambda: time.time() + 5)
        assert exp.grid.item_locations[(2, 2)].item_id == "sunflower_bud"

    def test_null_target(self, exp):
        from dlgr.griduniverse.experiment import Item

        item = Item(
            {
                "id": 1,
                "item_id": "sunflower_dried",
                "name": "Sunflower Dried",
                "n_uses": 1,
            }
        )
        exp.grid.item_locations[(2, 2)] = item

        exp.item_config["sunflower_sprout"]["auto_transition_target"] = None
        exp.grid.trigger_transitions(time=lambda: time.time() + 5)
        assert (2, 2) not in exp.grid.item_locations


@pytest.fixture(autouse=True)
def add_item_config(exp):
    """Make sure item configs needed for these tests are set"""
    exp.grid.item_config["sunflower_dried"] = {
        "name": "Sunflower dried",
        "item_id": "sunflower_dried",
        "n_uses": 1,
        "auto_transition_time": 5,
    }
    exp.grid.item_config["sunflower_sprout"] = {
        "auto_transition_target": "sunflower_bud",
        "auto_transition_time": 5,
        "n_uses": 1,
        "name": "Sunflower sprout",
    }
