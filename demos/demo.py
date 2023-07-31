from dallinger.experiments import Griduniverse

experiment = Griduniverse()
participants = 3

data = experiment.run(
    mode="debug",
    recruiter="bots",
    bot_policy="AdvantageSeekingBot",
    max_participants=participants,
    num_dynos_worker=participants,
)

results = experiment.analyze(data)

print(results)
