import math


def geometric(random, p):
    """Generate a geometric integer in the range [0, infinity) with expected
    value.

    1 / p - 1

    """
    denom = math.log1p(-p)
    return int(math.log(random.random()) / denom)


def biased_coin(random, p):
    return random.random() <= p
