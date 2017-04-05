from dallinger.experiments import Griduniverse

experiment = Griduniverse()

data = experiment.run(
    mode=u'debug',
    recruiter=u'bots',
)

print(data.networks.df)
