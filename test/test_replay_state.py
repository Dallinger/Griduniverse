"""Tests for the data module."""

from datetime import datetime
import pytest


class TestReplayState(object):

    @pytest.fixture
    def experiment(self, db_session):
        from dlgr.griduniverse.experiment import Griduniverse
        yield Griduniverse()

    @pytest.fixture
    def scrubber(self, experiment, db_session):
        with experiment.restore_state_from_replay(
            'griduniverse-test',
            session=db_session,
            zip_path='test/griduniverse_bots.zip',
        ) as scrubber:
            yield scrubber

    def test_forward_scrub_updates_state(self, scrubber, experiment):
        target = datetime(2018, 4, 5, 10, 32, 0, 0)
        scrubber(target)
        assert len(experiment.grid.food_locations) > 0
