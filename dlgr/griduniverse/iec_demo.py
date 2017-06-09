from dallinger.experiments import Griduniverse
from random import randint
import random
import logging
from bisect import bisect


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__file__)


class Offspring(object):
    """Generate offspring genome from parents"""

    def __init__(self, id, parents, weights, rate=.3):
        self.id = id
        self.rate = rate
        self.parents = parents
        self.weights = weights

    @property
    def genome(self):
        """Run genome logic"""
        options = self.weighted_rand(self.parents, self.weights)
        return self.mutate(options)

    def mutate(self, genome, rate=.3):
        """Percent of failed mutation copies"""
        if random.random() <= self.rate:
            logger.info("Mutation!")
            genome['show_chatroom'] = bool(random.getrandbits(1))
        if random.random() <= self.rate:
            logger.info("Mutation!")
            genome['num_food'] = randint(0,9)
        if random.random() <= self.rate:
            logger.info("Mutation!")
            genome['respawn_food'] = bool(random.getrandbits(1))
        return genome

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
                'num_food': randint(0,9),
                'respawn_food': bool(random.getrandbits(1))
        }

    def get_weights(self, players):
        """Generate a new genome"""
        logger.info("Offspring are selected based on survival.")
        fitness_denom = 0
        weights = []

        for player in xrange(players):
            fitness_denom += (float(self.scores[player]) / self.max_score)

        for player in xrange(players):
            score_decimal = float(self.scores[player]) / self.max_score
            prob_survival = float(score_decimal) / float(fitness_denom)
            logger.info("Survival %: {}".format(100.0 * float(prob_survival)))
            weights.append(prob_survival)
        return weights

    def player_feedback(self):
        """Random feedback generator"""
        feedback = randint(1,9)
        return feedback

    def run(self, players, generations):
        """Run evolutionary algorithm"""
        genomes = self.genomes
        for generation in xrange(generations):
            if (generation == 0):
                for player in xrange(players):
                    logger.info("Running generation {0} for Player {1}"
                                .format(generation + 1, player + 1)
                    )
                    genomes[player] = self.random_genome()
                    self.scores[player] = self.player_feedback()
                continue

            weights = self.get_weights(players)
            for player in xrange(players):
                child = Offspring(player, genomes.values(), weights)
                logger.info("Running generation {0} for Player {1}"
                            .format(generation + 1, player + 1)
                )
                genome = child.genome
                data = experiment.run(
                mode=u'debug',
                recruiter=u'bots',
                bot_policy=u"AdvantageSeekingBot",
                max_participants=self.participants,
                num_dynos_worker=self.participants,
                time_per_round=5.0,
                verbose=True,
                show_chatroom = genome['show_chatroom'],
                num_food = genome['num_food'],
                respawn_food = genome['respawn_food']
                )
                """Survivors is a dictionary of the current player's
                ID as a key, along with the user feedback score"""
                #survivors[player] = experiment.player_feedback(data)
                self.scores[player] = self.player_feedback()

        #results = experiment.analyze(data)
        results = "Done"
        return results


experiment = Griduniverse()
participants = 1
Evolve(2, 3)
