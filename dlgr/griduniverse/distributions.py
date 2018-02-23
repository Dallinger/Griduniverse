import numpy
import random
from numpy.random import choice
import matplotlib.pyplot as plt


class Distributions(object):
    """Given rows and columns, generate a distribution."""


    def __init__(self, rows, columns):
        self.rows = rows
        self.columns = columns

    def _random_probability_distribution(self, *args):
        """A probability distribution function always returns a [row, column] pair."""
        row = random.randint(0, self.rows - 1)
        column = random.randint(0, self.columns - 1)
        return [row, column]


    def _sinusoidal_probability_distribution(self, *args):
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


    def _standing_wave_probability_distribution(self, *args):
        # https://ocefpaf.github.io/python4oceanographers/blog/2013/11/25/waves/
        rows = self.rows
        cols = self.columns
        a = 1
        if len(args):
            try:
                a = int(args[0])
            except ValueError:
                pass
        d = 1
        t = 20
        w = 2 * numpy.pi / t
        k = w ** 2 / 9.81
        x = numpy.arange(rows * cols)
        a1 = (a ** 2 + a ** 2 + 2 * a * a * numpy.cos(2 * k * x + d)) ** (0.5)
        a2 = a * numpy.cos(k * x) + a * numpy.cos(k * x + d)
        a3 = a * numpy.sin(k * x) - a * numpy.sin(k * x + d)
        g = numpy.arctan2(a3, a2)
        p = a1 * numpy.cos(w * x - g)
        p = (p - numpy.min(p)) / (numpy.max(p) - numpy.min(p))
        p = p / numpy.sum(p)
        value = choice(rows * cols, p=p)
        row = value / cols
        column = value - (row * cols)
        return [row, column]


    def _gaussian_mixture_probability_distribution(self, *args):
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


    def _horizontal_gradient_probability_distribution(self, *args):
        rows = self.rows
        cols = self.columns
        cells = rows * cols
        grid = numpy.gradient(cells * numpy.random.random((rows, cols)), axis=0)
        grid = (grid - numpy.min(grid)) / (numpy.max(grid) - numpy.min(grid))
        grid = grid / numpy.sum(grid)
        value = choice(cells, p=grid.flatten())
        row = value / cols
        column = value - (row * cols)
        return [row, column]


    def _vertical_gradient_probability_distribution(self, *args):
        rows = self.rows
        cols = self.columns
        cells = rows * cols
        grid = numpy.gradient(cells * numpy.random.random((rows, cols)), axis=1)
        grid = (grid - numpy.min(grid)) / (numpy.max(grid) - numpy.min(grid))
        grid = grid / numpy.sum(grid)
        value = choice(cells, p=grid.flatten())
        row = value / cols
        column = value - (row * cols)
        return [row, column]


    def _edge_bias_probability_distribution(self, *args):
        rows = self.rows
        cols = self.columns
        values = range(rows * cols)
        for row in range(rows):
            for col in range(cols):
                values[row * cols + col] = 2
                if col == 2 or row == 2 or col == cols - 3 or row == rows - 3:
                    values[row * cols + col] = 4
                if col == 1 or row == 1 or col == cols - 2 or row == rows - 2:
                    values[row * cols + col] = 8
                if col == 0 or row == 0 or col == cols - 1 or row == rows - 1:
                    values[row * cols + col] = 16
        total = sum(values)
        for index, value in enumerate(values):
            values[index] = float(value) / float(total)
        value = choice(rows * cols, p=values)
        row = value / cols
        column = value - (row * cols)
        return [row, column]


    def _center_bias_probability_distribution(self, *args):
        rows = self.rows
        cols = self.columns
        values = range(rows * cols)
        for row in range(rows):
            for col in range(cols):
                values[row * cols + col] = 16
                if col == 2 or row == 2 or col == cols - 3 or row == rows - 3:
                    values[row * cols + col] = 8
                if col == 1 or row == 1 or col == cols - 2 or row == rows - 2:
                    values[row * cols + col] = 4
                if col == 0 or row == 0 or col == cols - 1 or row == rows - 1:
                    values[row * cols + col] = 2
        total = sum(values)
        for index, value in enumerate(values):
            values[index] = float(value) / float(total)
        value = choice(rows * cols, p=values)
        row = value / cols
        column = value - (row * cols)
        return [row, column]


if __name__ == "__main__":
    test = Distributions(100, 100)
    for i in xrange (1, 1000):
        coord = test._horizontal_gradient_probability_distribution()
        plt.plot(coord[0],coord[1], color='blue', marker='o')
    plt.show()
