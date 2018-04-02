from dallinger.experiments import Griduniverse
from learners import ActiveLearner
from query_strategies import (
    # BALD,
    HyperCubePool,
    RandomStrategy,
)

NDIM = 3
POOL_SIZE = 500
BUDGET = 10
BASE_KERNELS = ["PER", "LIN"]
DEPTH = 1

def scale_down(maxVal, dim):
    """Rescale 0 =< output =< 1"""
    out = float(dim/maxVal)
    return out

def scale_up(maxVal, dim):
    """Rescale up to actual values"""
    out = (dim/1.0) * maxVal
    return out

def oracle(x):
    """Run a GU game by scaling up the features so they can be input into the game.
    From these scaled up features, we may need to redefine our maximum thresholds.
    """
    MAX_AVG_SCORE = 1.0
    MAX_PARTICIPANTS = 1
    MAX_TIME_PER_ROUND = 20.0
    MAX_NUM_FOOD = 8
    experiment = Griduniverse()
    participants = scale_up(MAX_PARTICIPANTS, x[0])
    time_per_round = scale_up(MAX_TIME_PER_ROUND, x[1])
    num_food = scale_up(MAX_NUM_FOOD, x[2])
    MAX_PARTICIPANTS = max(MAX_PARTICIPANTS, participants)
    MAX_TIME_PER_ROUND = max(MAX_TIME_PER_ROUND, time_per_round)
    MAX_NUM_FOOD = max(MAX_NUM_FOOD, num_food)
    data = experiment.run(
    mode=u'debug',
    recruiter=u'bots',
    bot_policy=u"AdvantageSeekingBot",
    time_per_round = time_per_round,
    num_food = num_food,
    max_participants=participants,
    num_dynos_worker=participants,
    webdriver_type=u'chrome',
    )
    avg_score = float(experiment.analyze(data)['average_score'])
    # Scale back down
    results = scale_down(MAX_AVG_SCORE, avg_score)
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

