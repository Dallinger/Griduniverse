"""
Tests for `dlgr.griduniverse` module.
"""
import mock
import os
import pytest
import shutil
import tempfile


@pytest.fixture
def env():
    # Heroku requires a home directory to start up
    # We create a fake one using tempfile and set it into the
    # environment to handle sandboxes on CI servers

    fake_home = tempfile.mkdtemp()
    environ = os.environ.copy()
    environ.update({'HOME': fake_home})
    yield environ

    shutil.rmtree(fake_home, ignore_errors=True)


@pytest.fixture
def exp_dir():
    """Set up the environment by changing to the experiment dir."""
    orig_path = os.getcwd()
    os.chdir(os.path.join("dlgr", "griduniverse"))
    yield
    os.chdir(orig_path)


@pytest.fixture
def env_with_home(env):
    original_env = os.environ.copy()
    if 'HOME' not in original_env:
        os.environ.update(env)
    yield
    os.environ = original_env


@pytest.fixture
def config():
    from dallinger.config import get_config
    config = get_config()
    config.load()
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
def participant(db_session):
    from dallinger.models import Participant
    p = Participant(worker_id='1', hit_id='1', assignment_id='1', mode="test")
    db_session.add(p)
    db_session.flush()
    return p
