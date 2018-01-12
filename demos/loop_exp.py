from dallinger.experiments import Griduniverse

experiment = Griduniverse()
participants = 2
iterations = 10

for i in xrange(iterations):
    data = experiment.run(
        time_per_round = 5.0,
        mode=u'debug',
        max_participants=participants,
        num_dynos_worker=participants,
    )

    results = experiment.analyze(data)
    print(results)
