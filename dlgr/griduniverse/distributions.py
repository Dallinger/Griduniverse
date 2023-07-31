import random

import numpy


def _is_valid_boundary(rows, columns, row, column):
    """Truncate random sample"""
    if row < rows and row >= 0 and column < columns and column >= 0:
        return True
    return False


def random_probability_distribution(rows, columns, *args):
    """A probability distribution function always returns a [row, column] pair."""
    row = random.randint(0, rows - 1)
    column = random.randint(0, columns - 1)
    return [row, column]


def sinusoidal_probability_distribution(rows, columns, *args):
    frequency = 10
    if len(args):
        try:
            frequency = int(args[0])
        except ValueError:
            pass
    grid = numpy.tile(numpy.linspace(0, 1, columns), (rows, 1))
    p = 0.5 + 0.5 * numpy.sin(frequency * grid)
    p = p / numpy.sum(p)
    value = numpy.random.choice(rows * columns, p=p.flatten())
    row = value / columns
    column = value - (row * columns)
    return [int(row), int(column)]


def horizontal_gradient_probability_distribution(rows, columns, *args):
    """Vertical gradient on the x axis"""
    size = columns - 1
    column = random.randint(0, size)
    row = random.triangular(0, size, size)
    return [int(row), int(column)]


def vertical_gradient_probability_distribution(rows, columns, *args):
    """Vertical gradient on the y axis"""
    size = rows - 1
    row = random.randint(0, size)
    column = random.triangular(0, size, size)
    return [int(row), int(column)]


def edge_bias_probability_distribution(rows, columns, *args):
    """Do the inverse to a normal distribution"""
    mu = rows / 2  # mean
    sigma = 15  # standard deviation
    row = numpy.random.normal(mu, sigma)
    column = numpy.random.normal(mu, sigma)
    valid = False
    while not valid:
        if row > mu and column > mu:
            row = mu + numpy.random.normal(mu, sigma)
            column = random.randint(0, columns - 1)
        elif row > mu and column < mu:
            row = abs(numpy.random.normal(mu, sigma) - mu)
            column = random.randint(0, columns - 1)
        elif row < mu and column > mu:
            column = mu + numpy.random.normal(mu, sigma)
            row = random.randint(0, columns - 1)
        else:
            column = abs(numpy.random.normal(mu, sigma) - mu)
            row = random.randint(0, columns - 1)
        valid = _is_valid_boundary(rows, columns, row, column)
    return [int(row), int(column)]


def center_bias_probability_distribution(rows, columns, *args):
    """Do normal distribution in two dimensions"""
    mu = rows / 2  # mean
    sigma = 15  # standard deviation
    valid = False
    while not valid:
        row = numpy.random.normal(mu, sigma)
        column = numpy.random.normal(mu, sigma)
        # Create some cutoff for values
        valid = _is_valid_boundary(rows, columns, row, column)
    return [int(row), int(column)]
