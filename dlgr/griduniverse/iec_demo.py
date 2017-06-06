from dallinger.experiments import Griduniverse
from random import randint
import random

def get_genomes(players, survivors=None):
    """Given the surviving generation, generate a new genome"""
    genomes = {}
    if not survivors:
        for player in range(1, players):
            types = {
                    'show_chatroom': bool(random.getrandbits(1)),
                    'show_grid': bool(random.getrandbits(1)),
                    'num_food': randint(0,9),
                    'respawn_food': bool(random.getrandbits(1))
            }
            genomes[player] = types

    else:
        # Calculate survivors
        for player in range(1, players):
            types = {
                    'show_chatroom': bool(random.getrandbits(1)),
                    'show_grid': bool(random.getrandbits(1)),
                    'num_food': randint(0,9),
                    'respawn_food': bool(random.getrandbits(1))
            }
            genomes[player] = types
    return genomes


def evolve(players, generations, survivor=None):
    """Run evolutionary algorithm"""
    if generations==0:
        results = experiment.analyze(data)
        return results

    players_genomes = get_genomes(players, survivor)
    for player in range(1, players):
        genome = players_genomes[player]
        data = experiment.run(
        mode=u'debug',
        recruiter=u'bots',
        bot_policy=u"AdvantageSeekingBot",
        max_participants=participants,
        num_dynos_worker=participants,
        )
        survivor = experiment.get_survivors(data)
    evolve(players, generations-1, survivor)

experiment = Griduniverse()
participants = 1
n = 10
m = 10
evolve(n, m)
