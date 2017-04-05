from dallinger.experiments import Griduniverse

experiment = Griduniverse()

data = experiment.run(
    mode=u'debug',
    recruiter=u'bots',
    bot_policy=u"AdvantageSeekingBot",
    max_participants=1,
)

results = experiment.analyze(data)

print(results)
