"""
Test fixtures for `dlgr.griduniverse` module.
"""
import copy
import os
import shutil
import tempfile

import mock
import pytest
from dallinger import models

skip_on_ci = pytest.mark.skipif(
    bool(os.environ.get("CI", False)), reason="Only runs outside of CI environment"
)


@pytest.fixture(scope="module", autouse=True)
def reset_config():
    yield

    # Make sure dallinger_experiment module isn't kept between tests
    import sys

    if "dallinger_experiment" in sys.modules:
        del sys.modules["dallinger_experiment"]

    # Make sure extra parameters aren't kept between tests
    from dallinger.config import get_config

    config = get_config()
    config._reset(register_defaults=True)


@pytest.fixture(scope="session")
def env():
    # Heroku requires a home directory to start up
    # We create a fake one using tempfile and set it into the
    # environment to handle sandboxes on CI servers
    environ_orig = os.environ.copy()
    if not environ_orig.get("CI", False):
        yield environ_orig
    else:
        fake_home = tempfile.mkdtemp()
        environ_patched = environ_orig.copy()
        environ_patched.update({"HOME": fake_home})
        os.environ = environ_patched
        yield environ_patched
        os.environ = environ_orig
        shutil.rmtree(fake_home, ignore_errors=True)


@pytest.fixture
def exp_dir():
    """Set up the environment by changing to the experiment dir."""
    orig_path = os.getcwd()
    os.chdir(os.path.join("dlgr", "griduniverse"))
    yield
    os.chdir(orig_path)


@pytest.fixture
def stub_config():
    """Builds a standardized Configuration object and returns it, but does
    not load it as the active configuration returned by
    dallinger.config.get_config()
    """
    defaults = {
        "aws_region": "us-east-1",
        "base_port": 5000,
        "clock_on": True,
        "dallinger_email_address": "test@example.com",
        "database_url": "postgresql://postgres@localhost/dallinger",
        "dyno_type": "standard-2x",
        "heroku_team": "dallinger",
        "host": "localhost",
        "logfile": "server.log",
        "loglevel": 0,
        "mode": "debug",
        "num_dynos_web": 2,
        "num_dynos_worker": 2,
        "replay": False,
        "threads": "1",
        "whimsical": True,
    }
    from dallinger.config import Configuration, default_keys

    from dlgr.griduniverse.experiment import GU_PARAMS

    config = Configuration()
    for key in default_keys:
        config.register(*key)
    for key in GU_PARAMS.items():
        config.register(*key)

    config.extend(defaults.copy())
    # Patch load() so we don't update any key/value pairs from actual files:
    # (Note: this is blindly cargo-culted in from dallinger's equivalent fixture.
    # Not certain it's necessary here.)
    config.load = mock.Mock(side_effect=lambda: setattr(config, "ready", True))
    config.ready = True

    return config


@pytest.fixture
def active_config(stub_config):
    """Loads the standard config as the active configuration returned by
    dallinger.config.get_config() and returns it.
    """
    from dallinger import config as c

    orig_config = c.config
    c.config = stub_config
    yield c.config
    c.config = orig_config


@pytest.fixture
def item_config():
    return copy.deepcopy(
        {
            1: {
                "calories": 5,
                "crossable": True,
                "interactive": False,
                "item_count": 8,
                "item_id": 1,
                "maturation_speed": 0.01,
                "maturation_threshold": 0.5,
                "n_uses": 1,
                "name": "Food",
                "plantable": False,
                "planting_cost": 1,
                "portable": True,
                "probability_distribution": "random",
                "public_good": 0.0,
                "public_good_multiplier": 0.0,
                "respawn": True,
                "seasonal_growth_rate": 1.0,
                "spawn_rate": 1.0,
                "sprite": "#8a9b0f,#7a6b54",
            }
        }
    )


@pytest.fixture
def output():
    class Output(object):
        def __init__(self):
            self.log = mock.Mock()
            self.error = mock.Mock()
            self.blather = mock.Mock()

    return Output()


@pytest.fixture
def db_session():
    import dallinger.db

    # The drop_all call can hang without this; see:
    # https://stackoverflow.com/questions/13882407/sqlalchemy-blocked-on-dropping-tables
    dallinger.db.session.close()
    session = dallinger.db.init_db(drop_all=True)
    yield session
    session.rollback()
    session.close()


@pytest.fixture
def pubsub(game):
    import dallinger.db

    with mock.patch(
        "dlgr.griduniverse.experiment.db.redis_conn", autospec=dallinger.db.redis_conn
    ) as mock_redis:
        orig_conn = game.redis_conn
        game.redis_conn = mock_redis
        yield mock_redis
        game.redis_conn = orig_conn


@pytest.fixture
def fresh_gridworld():
    from dlgr.griduniverse.experiment import Gridworld

    if hasattr(Gridworld, "instance"):
        delattr(Gridworld, "instance")

    yield

    if hasattr(Gridworld, "instance"):
        delattr(Gridworld, "instance")


@pytest.fixture
def gridworld(fresh_gridworld, active_config, item_config):
    from dlgr.griduniverse.experiment import Gridworld

    gw = Gridworld(
        log_event=mock.Mock(), item_config=item_config, **active_config.as_dict()
    )
    yield gw


@pytest.fixture
def exp(db_session, active_config, fresh_gridworld):
    from dallinger.experiments import Griduniverse

    gu = Griduniverse(db_session)
    gu.app_id = "test app"
    gu.exp_config = active_config

    for game in gu.games_by_control_channel_id.values():
        game.grid.players.clear()

    yield gu

    for game in gu.games_by_control_channel_id.values():
        game.socket_session.rollback()
        game.socket_session.close()


@pytest.fixture
def game(exp):
    for game in exp.games_by_control_channel_id.values():
        yield game


@pytest.fixture
def fake_gsleep():
    with mock.patch("gevent.sleep") as fake_sleep:
        yield fake_sleep


@pytest.fixture
def a(db_session):
    """Provides a standard way of building model objects in tests.

    def test_using_all_defaults(self, a):
        participant = a.participant(worker_id=42)
    """

    class ModelFactory(object):
        def __init__(self, db):
            self.db = db

        def participant(self, **kw):
            defaults = {
                "recruiter_id": "hotair",
                "worker_id": "1",
                "assignment_id": "1",
                "hit_id": "1",
                "mode": "test",
            }
            defaults.update(kw)
            return self._build(models.Participant, defaults)

        def network(self, **kw):
            defaults = {}
            defaults.update(kw)
            return self._build(models.Network, defaults)

        def _build(self, klass, attrs):
            # Some of our default values are factories:
            for k, v in attrs.items():
                if callable(v):
                    attrs[k] = v()

            obj = klass(**attrs)
            self._insert(obj)
            return obj

        def _insert(self, thing):
            db_session.add(thing)
            db_session.flush()  # This gets us an ID and sets relationships

    return ModelFactory(db_session)


@pytest.fixture
def participants(db_session, a):
    ps = []
    for i in range(10):
        p = a.participant(worker_id=str(i))
        ps.append(p)
        db_session.add(p)
        db_session.flush()
    return ps
