"""
Tests for `dlgr.griduniverse` module.
"""
import mock
import os
import pytest
import shutil
import tempfile
import time
from dallinger.experiments import Griduniverse


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
def env_with_home(env):
    original_env = os.environ.copy()
    if 'HOME' not in original_env:
        os.environ.update(env)
    yield
    os.environ = original_env


@pytest.fixture
def output():

    class Output(object):

        def __init__(self):
            self.log = mock.Mock()
            self.error = mock.Mock()
            self.blather = mock.Mock()

    return Output()


class TestGriduniverse(object):

    @classmethod
    def setup(cls):
        pass

    def test_bot_api(self):
        """Run bots using headless chrome and collect data."""
        self.experiment = Griduniverse()
        data = self.experiment.run(
                mode=u'debug',
                webdriver_type=u'chrome',
                recruiter=u'bots',
                bot_policy=u"AdvantageSeekingBot",
                max_participants=1,
                num_dynos_worker=1,
                time_per_round=30.0,
           )
        results = self.experiment.average_score(data)
        assert results > 0

    @classmethod
    def teardown(cls):
        pass

class Saucelabs(object):

    def setup(self):
        desired_capabilities = {'browserName': 'chrome'}
        desired_capabilities['version'] = '11'
        desired_capabilities['platform'] = 'Mac 10.10'
        desired_capabilities['name'] = 'Capture screenshot with WebDriver'

        self.driver = webdriver.Remote(
            desired_capabilities=desired_capabilities,
            command_executor="http://USERNAME:ACCESS-KEY@ondemand.saucelabs.com:80/wd/hub")
        self.driver.implicitly_wait(10)

    def test_sauce(self):
        """Example request"""
        self.driver.get('http://google.com')
        sesh = self.driver.session_id
        print "Link to your job: https://saucelabs.com/jobs/%s" % sesh
        data = self.experiment.run(
                mode=u'debug',
                webdriver_type=u'chrome',
                recruiter=u'bots',
                bot_policy=u"AdvantageSeekingBot",
                max_participants=1,
                num_dynos_worker=1,
                time_per_round=30.0,
           )
        self.driver.get_screenshot_as_file('griduniverse.png')

    def teardown(self):
        self.driver.quit()

class TestCommandline(object):

    def setup(self):
        """Set up the environment by changing to the experiment dir."""
        self.orig_path = os.getcwd()
        os.chdir(os.path.join("dlgr", "griduniverse"))

    def teardown(self):
        os.chdir(self.orig_path)

    @pytest.fixture
    def debugger_unpatched(self, env_with_home, output):
        from dallinger.command_line import DebugSessionRunner
        debugger = DebugSessionRunner(output, verbose=True, bot=False, exp_config={})
        return debugger

    @pytest.fixture
    def debugger(self, debugger_unpatched):
        from dallinger.heroku.tools import HerokuLocalWrapper
        debugger = debugger_unpatched
        debugger.notify = mock.Mock(return_value=HerokuLocalWrapper.MONITOR_STOP)
        return debugger

    def test_startup(self, debugger):
        debugger.run()
        "Server is running" in str(debugger.out.log.call_args_list[0])

    def test_raises_if_heroku_wont_start(self, debugger):
        mock_wrapper = mock.Mock(
            __enter__=mock.Mock(side_effect=OSError),
            __exit__=mock.Mock(return_value=False)
        )
        with mock.patch('dallinger.command_line.HerokuLocalWrapper') as Wrapper:
            Wrapper.return_value = mock_wrapper
            with pytest.raises(OSError):
                debugger.run()
