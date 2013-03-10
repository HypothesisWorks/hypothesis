from hypothesis.generate import generator
from hypothesis.minimize import minimize_such_that 
from itertools import islice

def falsify(hypothesis, *argument_types, **kwargs):
    def default_argument(name, value):
        try:
            kwargs[name]
        except KeyError:
            kwargs[name] = value

    default_argument("max_size", 1024)
    default_argument("probe_size", 10)

    gen = generator(argument_types)

    def falsifies(args):
        for x,t in zip(args, argument_types):
            assert isinstance(x,t)
        try:
            return not hypothesis(*args)
        except AssertionError:
            return True

    def find_falsifier():
        size = 1
        while size <= kwargs["max_size"]:
            for x in islice(gen(size),kwargs["probe_size"]):
                if falsifies(x): 
                    return x
            size *= 2
        raise Unfalsifiable()

    starting_point = find_falsifier()

    return minimize_such_that(starting_point, falsifies) 
   

class Unfalsifiable(Exception):
    def __init__(self):
        Exception.__init__(self, "Unable to falsify hypothesis")
