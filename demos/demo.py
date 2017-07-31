from dallinger.experiments import Griduniverse

experiment = Griduniverse()
participants = 20

data = experiment.run(
    webdriver_type=u'chrome',
    mode=u'sandbox',
    recruiter=u'bots',
    bot_policy=u"AdvantageSeekingBot",
    max_participants=participants,
    num_dynos_worker=participants,
)

results = experiment.analyze(data)

print(results)
