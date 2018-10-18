from dallinger.experiments import Griduniverse
from bams.learners import ActiveLearner
from bams.query_strategies import (
    BALD,
    HyperCubePool,
    RandomStrategy,
)

NDIM = 1
POOL_SIZE = 500
BUDGET = 10
BASE_KERNELS = ["PER", "LIN", "K", "SE"]
DEPTH = 1

collected_data = {}

def num_colors(x):
    """x is the fraction of the total players who are on a single team"""
    return int(round(1.0 / x))

def closest_valid_x(x):
    x = x[0]
    x = max(1.0/6.0, x)  # 1/6 is the lowest valid value as we have at most 6 teams
    num_teams = num_colors(x)
    return (1.0 / num_teams, )

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
    grid_config = {
        "mode": u'live',
        "recruiter": u'mturk',
        "bot_policy": u"AdvantageSeekingBot",
        u'contact_email_on_error': u"dallinger-admin@lists.berkeley.edu",
        "contact_email_on_error": u"dallinger-admin@lists.berkeley.edu",
        u'organization_name': u'UC Berkeley',
        u'description': u'Play an interactive game',
        "dyno_type": u"performance-l",
        "redis_size": u"premium-5",
        "num_dynos_worker": 4,
        "num_dynos_web": 1,
        "max_participants": 12,
        "num_recruits": 24,
        "time_per_round": 60.0,
        "num_food": 100,
        "num_colors": num_colors(x[0]),
        "intergroup_competition": 100.0,
        "intragroup_competition": 0.0,
        "duration": 0.5,
        "base_payment": 3.0,
    }
    experiment = Griduniverse()
    data = experiment.run(**grid_config)
    score = experiment.average_score(data) * 12
    results = scale_down(1000, score)
    collected_data[data.source] = grid_config
    return results

def main():
    learner = ActiveLearner(
        query_strategy=BALD(dim=NDIM),
        budget=BUDGET,
        base_kernels=BASE_KERNELS,
        max_depth=DEPTH,
        ndim=NDIM,
    )

    while learner.budget > 0:
        x = learner.next_query()
        x = closest_valid_x(x)
        y = learner.query(oracle, x)
        print x, y
        learner.update(x, y)
        print(learner.posteriors)
        print(learner.map_model)
    import pdb; pdb.set_trace()
    print collected_data


if __name__ == '__main__':
    main()
