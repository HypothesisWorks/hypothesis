"""
This is a module for functions I consider to be designed to work around Python
doing entirely the wrong thing.

You can imagine how grumpy I was when I wrote it.
"""


def actually_equal(x, y):
    return (type(x) == type(y)) and (x == y)


def actually_in(x, ys):
    return any(actually_equal(x, y) for y in ys)
