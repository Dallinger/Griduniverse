from dallinger.experiments import Griduniverse

experiment = Griduniverse()
participants = 1
iterations = 2

for i in xrange(iterations):
    data = experiment.run(
        time_per_round = 100.0,
        mode=u'sandbox',
        max_participants=participants,
        num_dynos_worker=participants,
    )

    results = experiment.analyze(data)
    print(results)

print("Script successfully ran with %d participants for %d iterations" % (participants, iterations))

