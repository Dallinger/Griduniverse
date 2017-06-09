from dallinger.experiments import Griduniverse
from random import randint
import random
import logging
from bisect import bisect


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__file__)


class Offspring(object):
    """Generate offspring genome from parents"""

    def __init__(self, id, parents, scores, mutation_rate=.3):
        self.id = id
        self.mutation_rate = mutation_rate
        self.parents = parents
        self.scores = scores
        self.max_score = 7.0

    @property
    def genome(self):
        """Run genome logic"""
        weights = self.get_weights(self.players, self.scores)
        options = self.weighted_rand(self.parents, weights)
        return self.mutate(options)

    def mutate(self, genome):
        """Percent of failed mutation copies"""
        if random.random() <= self.mutation_rate:
            logger.info("Mutation!")
            genome['show_chatroom'] = bool(random.getrandbits(1))
        if random.random() <= self.mutation_rate:
            logger.info("Mutation!")
            genome['num_food'] = randint(0, 9)
        if random.random() <= self.mutation_rate:
            logger.info("Mutation!")
            genome['respawn_food'] = bool(random.getrandbits(1))
        return genome

    def get_weights(self, players, scores):
        """Generate Survival"""
        logger.info("Weights are selected based on parent survival.")
        fitness_denom = 0
        weights = []

        for player, value in enumerate(parents):
            fitness_denom += (float(scores[player]) / self.max_score)

        for player, value in enumerate(parents):
            score_decimal = float(scores[player]) / self.max_score
            prob_survival = float(score_decimal) / float(fitness_denom)
            logger.info("Survival %: {}".format(100.0 * float(prob_survival)))
            weights.append(prob_survival)
        return weights

    def weighted_rand(self, values, weights):
        """Weighted random value based on fitness"""
        total = 0
        cum_weights = []
        for w in weights:
            total += w
            cum_weights.append(total)
        x = random.random() * total
        i = bisect(cum_weights, x)
        return values[i]


class Evolve(object):
    """Construct N x M iteractive evolutionary algorithm"""

    def __init__(self, n, m):
        self.scores = {}
        self.participants = 1
        self.genomes = {}
        self.n = n
        self.m = m
        self.max_score = 7.0
        self.run(n, m)

    def random_genome(self):
        """Generate random genome"""
        logger.info("Generation 1 parents are being randomly intialized.")
        return {
                'show_chatroom': bool(random.getrandbits(1)),
                'num_food': randint(0, 9),
                'respawn_food': bool(random.getrandbits(1))
        }

    def player_feedback(self):
        """Random feedback generator"""
        feedback = randint(1, 9)
        return feedback

    def run(self, players, generations):
        """Run evolutionary algorithm"""
        scores = {}
        genomes = self.genomes
        for generation in xrange(generations):
            if (generation == 0):
                for player in xrange(players):
                    logger.info("Running generation {0} for Player {1}"
                                .format(generation + 1, player + 1))
                    genomes[player] = self.random_genome()
                    scores[player] = self.player_feedback()
                continue

            for player in xrange(players):
                child = Offspring(player, genomes.values(), scores, mutation_rate=.1)
                logger.info("Running generation {0} for Player {1}"
                            .format(generation + 1, player + 1))
                data = experiment.run(
                    mode=u'debug',
                    recruiter=u'bots',
                    bot_policy=u"AdvantageSeekingBot",
                    max_participants=self.participants,
                    num_dynos_worker=self.participants,
                    time_per_round=5.0,
                    verbose=True,
                    show_chatroom=child.genome['show_chatroom'],
                    num_food=child.genome['num_food'],
                    respawn_food=child.genome['respawn_food']
                )
                """Survivors is a dictionary of the current player's
                ID as a key, along with the user feedback score"""
                # survivors[player] = experiment.player_feedback(data)
                scores[player] = self.player_feedback()

        # results = experiment.analyze(data)
        results = "Done"
        return results


experiment = Griduniverse()
participants = 1
Evolve(2, 3)
