"""The Griduniverse."""

import dallinger


class Griduniverse(dallinger.experiments.Experiment):
    """Define the structure of the experiment."""

    def __init__(self, session):
        """Initialize the experiment."""
        super(Griduniverse, self).__init__(session)
        self.experiment_repeats = 1
        self.initial_recruitment_size = 1
        self.setup()
