from dallinger.experiments import Griduniverse
from bams.learners import ActiveLearner
from bams.query_strategies import (
    # BALD,
    HyperCubePool,
    RandomStrategy,
)

NDIM = 1
POOL_SIZE = 500
BUDGET = 10
BASE_KERNELS = ["PER", "LIN"]
DEPTH = 1


def scale_up(threshold, dim):
    """Rescale up to actual values"""
    out = int(dim * threshold)
    return out

def scale_down(threshold, dim):
    """Rescale 0 =< output =< 1"""
    out = float(dim/threshold) if threshold else 0.0
    return out

def oracle(x):
    """Run a GU game by scaling up the features so they can be input into the game.
    Then scale them done so the active learner can understand them.
    """
    grid_config = {"participants": 1,
                   "time_per_round": 20.0,
                   "num_food": 100,
                   "average_score": 200.0,
                }
    experiment = Griduniverse()
    # Scale up
    print x[0]
    num_food = scale_up(grid_config['num_food'], float(x[0]))
    print num_food
    data = experiment.run(
    mode=u'debug',
    recruiter=u'bots',
    bot_policy=u"AdvantageSeekingBot",
    time_per_round = grid_config['time_per_round'],
    num_food = num_food,
    max_participants=grid_config['participants'],
    num_dynos_worker=grid_config['participants'],
    webdriver_type=u'chrome',
    )
    score = experiment.average_score(data)
    print score
    # Scale back down
    results = scale_down(grid_config['average_score'], score)
    return results

learner = ActiveLearner(
    query_strategy=RandomStrategy(pool=HyperCubePool(NDIM, POOL_SIZE)),
    budget=BUDGET,
    base_kernels=BASE_KERNELS,
    max_depth=DEPTH,
    ndim=NDIM,
)

while learner.budget > 0:
    x = learner.next_query()
    y = learner.query(oracle, x)
    learner.update(x, y)
    print(learner.posteriors)
    print(learner.map_model)

