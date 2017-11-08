"""
Test fixtures for `dlgr.griduniverse` module.
"""
import mock
import os
import pytest
import shutil
import tempfile
from dallinger import models


skip_on_ci = pytest.mark.skipif(
    bool(os.environ.get('CI', False)),
    reason="Only runs outside of CI environment"
)


@pytest.fixture(scope='session')
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
        environ_patched.update({'HOME': fake_home})
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
        u'aws_region': u'us-east-1',
        u'base_port': 5000,
        u'clock_on': True,
        u'dallinger_email_address': u'test@example.com',
        u'database_url': u'postgresql://postgres@localhost/dallinger',
        u'dyno_type': u'standard-2x',
        u'heroku_team': u'dallinger',
        u'host': u'localhost',
        u'logfile': u'server.log',
        u'loglevel': 0,
        u'mode': u'debug',
        u'num_dynos_web': 2,
        u'num_dynos_worker': 2,
        u'threads': u'1',
        u'whimsical': True
    }
    from dallinger.config import default_keys
    from dallinger.config import Configuration
    config = Configuration()
    for key in default_keys:
        config.register(*key)
    config.extend(defaults.copy())
    config.ready = True

    return config


@pytest.fixture
def active_config(stub_config):
    """Loads the standard config as the active configuration returned by
    dallinger.config.get_config() and returns it.
    """
    from dallinger.config import get_config
    config = get_config()
    config.data = stub_config.data
    config.ready = True
    return config


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
def fresh_gridworld():
    from dlgr.griduniverse.experiment import Gridworld
    if hasattr(Gridworld, 'instance'):
        delattr(Gridworld, 'instance')


@pytest.fixture
def exp(db_session, active_config, fresh_gridworld):
    from dallinger.experiments import Griduniverse
    gu = Griduniverse(db_session)
    gu.app_id = 'test app'
    gu.exp_config = active_config
    gu.grid.players.clear()

    return gu


@pytest.fixture
def a(db_session):
    """ Provides a standard way of building model objects in tests.

        def test_using_all_defaults(self, a):
            participant = a.participant(worker_id=42)
    """
    class ModelFactory(object):

        def __init__(self, db):
            self.db = db

        def participant(self, **kw):
            defaults = {
                'worker_id': '1',
                'assignment_id': '1',
                'hit_id': '1',
                'mode': 'test'
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
def participants(db_session):
    from dallinger.models import Participant
    ps = []
    for i in range(10):
        p = Participant(worker_id=str(i), hit_id='1', assignment_id='1', mode="test")
        ps.append(p)
        db_session.add(p)
        db_session.flush()
    return ps
