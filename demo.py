import json

from dallinger.experiments import Griduniverse


def average_score(data):
    final_state = json.loads(data.infos.list[-1][-1])
    players = final_state['players']
    scores = [player['score'] for player in players]
    return float(sum(scores)) / len(scores)


experiment = Griduniverse()

data = experiment.run(
    mode=u'debug',
    recruiter=u'bots',
)

print(average_score(data))
