from dallinger.experiments import Griduniverse
from numpy.random import choice
from random import randint
from bisect import bisect
import random
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__file__)


class Offspring(object):
    """Generate genome from M-1 generation."""
    MAX_SCORE = 7.0

    def __init__(self, id, parents, scores, mutation_rate):
        self.id = id
        self.mutation_rate = mutation_rate
        self.parents = parents
        self.scores = scores

    @property
    def genome(self):
        """Run genome logic"""
        if bool(self.parents):
            weights = self.generate_weights(self.scores)
            options = self.weighted_rand(self.parents, weights)
            return self.mutate(options)
        return self.randomize_genome()

    def randomize_genome(self):
        """Generate random genome for generation 1"""
        return {
                'time_per_round': int(random.gauss(100, 15)),
                'show_chatroom': bool(random.getrandbits(1)),
                'num_food': int(random.gauss(10, 2)),
                'respawn_food': bool(random.getrandbits(1)),
                'rows': int(random.gauss(40, 5)),
                'columns': int(random.gauss(40, 5)),
                'block_size': int(random.gauss(5, 3)),
                'background_animation': bool(random.getrandbits(1)),
        }

    def mutate(self, genome):
        """Mutate genes according to mutation_rate"""
        for gene in genome.keys():
            if random.random() <= self.mutation_rate:
                logger.info("Mutation! Changing {}".format(gene))
                if type(genome[gene]) is bool:
                    genome[gene] = bool(random.getrandbits(1))
                elif genome[gene] == 'time_per_round':
                    int(random.gauss(5, 3))
                elif genome[gene] == 'rows' or genome[gene] == 'columns':
                    int(random.gauss(40, 5))
                elif genome[gene] == 'block_size':
                    int(random.gauss(5, 3))
                elif type(genome[gene]) is int:
                    int(random.gauss(10, 2))
            else:
                logger.info("Copied {} successfully".format(gene))
        return genome

    def generate_weights(self, scores):
        """Generate probability of survival"""
        logger.info("Weights are selected based on parent survival.")
        weights = []
        fitness_denom = 0

        for player, value in enumerate(self.parents):
            fitness_denom += (float(scores[player]) / self.MAX_SCORE)

        for player, value in enumerate(self.parents):
            score_decimal = float(scores[player]) / self.MAX_SCORE
            prob_survival = float(score_decimal) / float(fitness_denom)
            logger.info("Survival %: {}".format(100.0 * float(prob_survival)))
            weights.append(prob_survival)
        return weights

    def weighted_rand(self, values, weights):
        """Generate random value using weighted probabilities"""
        total = 0
        weightList = []
        for weight in weights:
            total += weight
            weightList.append(total)
        randomPoint = random.random() * total
        randomIndex = bisect(weightList, randomPoint)
        return values[randomIndex]


class Evolve(object):
    """N x M iteractive evolutionary algorithm"""
    TIME_PER_ROUND = 5.00
    scores = {}
    genomes = {}

    def __init__(self, n, m, bot=False, mutation_rate=.1):
        """Run experiment loop"""
        logger.info("Begin {0} x {1} experiment, bot={2}, mutation_rate={3}."
                    .format(n, m, bot, mutation_rate))
        self.n = n
        self.m = m
        self.bot = bot
        self.mutation_rate = mutation_rate
        self.recruiter = u'bots' if bot else u'None'
        self.bot_policy = u'AdvantageSeekingBot' if bot else u'None'
        self.run(n, m)

    def player_feedback(self, currPay, lastPay, feedback):
        """Generate feedback based on dollars earned."""
        low = .05 * self.TIME_PER_ROUND
        high = .25 * self.TIME_PER_ROUND
        if lastPay == 0:
            if currPay <= low:
                return 1
            elif currPay >= high:
                return 5
            else:
                return 3
        if (currPay - lastPay) >= .50:
            return feedback + 1
        elif abs(currPay - lastPay) <= .25:
            return feedback
        else:
            return feedback - 1

    def run(self, players, generations):
        """Run evolutionary algorithm"""
        scores = self.scores
        genomes = self.genomes
        lastPay = 0
        feedback = 0
        for generation in xrange(generations):
            for player in xrange(players):
                child = Offspring(player, genomes.values(), scores, self.mutation_rate)
                genomes[player] = child.genome
                logger.info("Running player {0} for generation {1}."
                            .format(player+1, generation+1))
                data = experiment.run(
                    mode=u'debug',
                    recruiter=self.recruiter,
                    bot_policy=self.bot_policy,
                    max_participants=1,
                    num_dynos_worker=1,
                    time_per_round=self.TIME_PER_ROUND,
                    verbose=True,
                    show_chatroom=genomes[player]['show_chatroom'],
                    num_food=genomes[player]['num_food'],
                    respawn_food=genomes[player]['respawn_food'],
                    columns=genomes[player]['columns'],
                    rows=genomes[player]['rows'],
                    block_size=genomes[player]['block_size'],
                    background_animation=genomes[player]['background_animation'],
                )
                if self.bot:
                    if player-1 in scores:
                        feedback = scores[player-1]
                    currPay = experiment.average_score(data)
                    scores[player] = self.player_feedback(
                                    currPay, lastPay, feedback)
                    last = currPay
                else:
                    scores[player] = experiment.player_feedback(data)[2]

        results = experiment.player_feedback(data)
        logger.info("Engagement:{0}, Difficulty:{1}, Fun:{2}"
                    .format(results[0], results[1], results[2]))

experiment = Griduniverse()
Evolve(2, 3, bot=True, mutation_rate=.2)
