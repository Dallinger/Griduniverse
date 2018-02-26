import numpy
import random
from numpy.random import choice
import matplotlib.pyplot as plt


class Distributions(object):
    """Given rows and columns, generate a distribution."""


    def __init__(self, rows, columns):
        self.rows = rows
        self.columns = columns
        self.limit = min(self.rows, self.columns)

    def random_probability_distribution(self, *args):
        """A probability distribution function always returns a [row, column] pair."""
        row = random.randint(0, self.rows - 1)
        column = random.randint(0, self.columns - 1)
        return [row, column]


    def sinusoidal_probability_distribution(self, *args):
        rows = self.rows
        cols = self.columns
        frequency = 10
        if len(args):
            try:
                frequency = int(args[0])
            except ValueError:
                pass
        grid = numpy.tile(numpy.linspace(0, 1, cols), (rows, 1))
        p = 0.5 + 0.5 * numpy.sin(frequency * grid)
        p = p / numpy.sum(p)
        value = choice(rows * cols, p=p.flatten())
        row = value / cols
        column = value - (row * cols)
        return [row, column]


    def standing_wave_probability_distribution(self, *args):
        size = self.columns - 1
        mu = (self.columns - 1) / 2
        column = random.randint(0, size)
        row = random.triangular(0, size, mu)
        return [row, column]


    def gaussian_mixture_probability_distribution(self, *args):
        rows = self.rows
        cols = self.columns
        k = 2
        if len(args):
            try:
                k = int(args[0])
            except ValueError:
                pass
        sd = 1
        if len(args) > 1:
            try:
                sd = int(args[1])
            except ValueError:
                pass
        if 'gaussian_means' not in self.food_probability_info:
            means = [(random.randint(0, cols - 1), random.randint(0, rows - 1))
                     for _ in range(k)]
            (row_mean, col_mean) = random.choice(means)
            self.food_probability_info['gaussian_means'] = (row_mean, col_mean)
        row_mean = self.food_probability_info['gaussian_means'][0]
        col_mean = self.food_probability_info['gaussian_means'][1]
        proposed = None
        while proposed is None:
            proposed_row = round(random.normalvariate(row_mean, sd))
            proposed_col = round(random.normalvariate(col_mean, sd))
            if (0 <= proposed_row < rows) and (0 <= proposed_col < cols):
                proposed = [proposed_row, proposed_col]
        return proposed


    def horizontal_gradient_probability_distribution(self, *args):
        """Vertical gradient on the x axis"""
        size = self.columns - 1
        column = random.randint(0, size)
        row = random.triangular(0, size, size)
        return [row, column]


    def vertical_gradient_probability_distribution(self, *args):
        """Vertical gradient on the y axis"""
        size = self.rows - 1
        row = random.randint(0, size)
        column = random.triangular(0, size, size)
        return [row, column]


    def edge_bias_probability_distribution(self, *args):
        """Do the inverse to a normal distribution """
        mu = self.rows / 2 # mean
        sigma = 15  # standard deviation
        row = numpy.random.normal(mu, sigma)
        column = numpy.random.normal(mu, sigma)
        valid = False
        while not valid:
            if row > mu and column > mu:
                row = (mu + numpy.random.normal(mu, sigma))
                column = random.randint(0, self.columns - 1)
            elif row > mu and column < mu:
                row = abs(numpy.random.normal(mu, sigma) - mu)
                column = random.randint(0, self.columns - 1)
            elif row < mu and column > mu:
                column = mu + numpy.random.normal(mu, sigma)
                row  = random.randint(0, self.columns - 1)
            else:
                column = abs(numpy.random.normal(mu, sigma) - mu)
                row  = random.randint(0, self.columns - 1)
            valid = self.valid_boundary(row, column)
        return [row, column]


    def center_bias_probability_distribution(self, *args):
        """Do normal distribution in two dimensions"""
        mu = self.rows / 2 # mean
        sigma = 15  # standard deviation
        while True:
            row = numpy.random.normal(mu, sigma)
            column = numpy.random.normal(mu, sigma)
            # Create some cutoff for values
            if row < self.rows and row >= 0 and column < self.columns and column >= 0:
                break
        return [row, column]

    def valid_boundary(self, row, column):
        if row < self.rows and row >= 0 and column < self.columns and column >= 0:
            return True
        return False

if __name__ == "__main__":
    test = Distributions(100, 100)
    for i in xrange (1, 1000):
        coord = test.edge_bias_probability_distribution()
        plt.plot(coord[0],coord[1], color='blue', marker='o')
    plt.show()
