"""
Tests for `dlgr.griduniverse` module.
"""
import mock
import pytest
from dallinger.experiments import Griduniverse


class TestDependenciesLoaded(object):

    def test_odo_importable(self):
        import odo
        assert odo is not None

    def test_tablib_importable(self):
        import tablib
        assert tablib is not None


@pytest.mark.usefixtures('env_with_home', 'config')
class TestExperimentClass(object):

    @pytest.fixture
    def exp(self, db_session, config):
        gu = Griduniverse(db_session)
        gu.app_id = 'test app'
        gu.exp_config = config

        return gu

    def test_initialization(self, exp):
        from dallinger.experiment import Experiment
        assert isinstance(exp, Experiment)

    def test_recruiter(self, exp):
        from dallinger.recruiters import Recruiter
        assert isinstance(exp.recruiter, Recruiter)

    def test_has_grid(self, exp):
        from dlgr.griduniverse.experiment import Gridworld
        assert isinstance(exp.grid, Gridworld)

    def test_create_network(self, exp):
        from dallinger.networks import FullyConnected
        net = exp.create_network()
        assert isinstance(net, FullyConnected)

    def test_session(self, exp, db_session):
        # Experiment creates its own session despite being passed one in the
        # __init__() method. Odd?
        assert exp.session is not db_session()

    def test_environment(self, exp):
        exp.environment.network in exp.networks()

    def test_recruit(self, exp):
        exp.recruit()

    def test_handle_connect_creates_node(self, exp, participant):
        exp.handle_connect({'player_id': participant.id})
        assert participant.id in exp.node_by_player_id

    def test_handle_connect_adds_player_to_grid(self, exp, participant):
        exp.handle_connect({'player_id': participant.id})
        assert participant.id in exp.grid.players

    def test_handle_connect_is_noop_for_spectators(self, exp):
        exp.handle_connect({'player_id': 'spectator'})
        assert exp.node_by_player_id == {}

    def test_records_events(self, exp, participant, config):
        exp.handle_connect({'player_id': participant.id})
        exp.send(
            'griduniverse_ctrl:{"type":"move","player_id":1,"move":"left"}'
        )
        data = exp.retrieve_data()
        assert (
            data.infos.dict['details'] ==
            u'{"move": "left", "type": "move", "actual": "left", "player_id": 1}'
        )
        results = self.experiment.average_score(data)
        assert results >= 0.0


@pytest.mark.usefixtures('exp_dir', 'env_with_home')
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


# @pytest.mark.usefixtures('env_with_home')
# class TestGriduniverse(object):

#     def test_bot_api(self):
#         """Run bots using headless chrome and collect data."""
#         self.experiment = Griduniverse()
#         data = self.experiment.run(
#             mode=u'debug',
#             webdriver_type=u'chrome',
#             recruiter=u'bots',
#             bot_policy=u"AdvantageSeekingBot",
#             max_participants=1,
#             num_dynos_worker=1,
#             time_per_round=20.0,
#         )
#         results = self.experiment.average_score(data)
#         assert results > 0
