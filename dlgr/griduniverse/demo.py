from dallinger.experiments import Griduniverse

experiment = Griduniverse()
participants = 1

data = experiment.run(
    mode=u'debug',
    webdriver_type=u'chrome',
    recruiter=u'bots',
    bot_policy=u"AdvantageSeekingBot",
    max_participants=participants,
    num_dynos_worker=participants,
    time_per_round=10.0,
)

results = experiment.analyze(data)

print(results)
