import math


def geometric(random, p):
    denom = math.log1p(-p)
    return int(math.log(random.random()) / denom)


def biased_coin(random, p):
    return random.random() <= p
