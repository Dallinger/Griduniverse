"""
Test fixtures for `dlgr.griduniverse` module.
"""
import mock
import os
import pytest
import shutil
import tempfile


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
