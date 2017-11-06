"""
Tests for `dlgr.griduniverse` module.
"""
import mock
import pytest
from dallinger.experiments import Griduniverse


@pytest.mark.usefixtures('env', 'config')
class TestExperimentClass(object):

    @pytest.fixture
    def exp(self, db_session, config):
        gu = Griduniverse(db_session)
        gu.app_id = 'test app'
        gu.exp_config = config

        return gu

    def test_donations_distributed_evenly_across_team(self, exp):
        pass


@pytest.mark.usefixtures('env')
class TestGriduniverseBotExecution(object):

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
            time_per_round=10.0,
        )
        results = self.experiment.average_score(data)
        assert results >= 0.0


@pytest.mark.usefixtures('exp_dir', 'env')
class TestCommandline(object):

    @pytest.fixture
    def debugger_unpatched(self, output):
        from dallinger.command_line import DebugSessionRunner
        debugger = DebugSessionRunner(
            output, verbose=True, bot=False, proxy_port=None, exp_config={}
        )
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
