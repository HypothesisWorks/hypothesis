from hypothesis.produce import producer
from hypothesis.simplify import Simplifiers
from itertools import islice

def assume(condition):
    if not condition: raise UnsatisfiedAssumption()

def falsify(hypothesis, *argument_types, **kwargs):
    def option(name, value):
        try:
            return kwargs[name]
        except KeyError:
            return value

    max_size = option("max_size", 1024)
    first_probe_size = option("first_probe_size", 10)
    second_probe_size = option("second_probe_size", 50)
    simplifiers = option("simplifiers", Simplifiers())

    gen = producer(argument_types)

    def falsifies(args):
        try:
            return not hypothesis(*args)
        except AssertionError:
            return True
        except UnsatisfiedAssumption:
            return False

    size = 1
    falsifying_example = None
    while not falsifying_example and size <= max_size:
        for _ in xrange(first_probe_size):
            x = gen(size)
            if falsifies(x): 
                falsifying_example = x
                break
        size *= 2

    if not falsifying_example: raise Unfalsifiable(hypothesis)

    while size > 1:
        size /= 2
        for _ in xrange(second_probe_size):
            x = gen(size)
            if falsifies(x): 
                falsifying_example = x
                break
        else:
            break

    return simplifiers.simplify_such_that(falsifying_example, falsifies) 
  
class UnsatisfiedAssumption(Exception):
    def __init__(self):
        Exception.__init__(self, "Unsatisfied assumption")

 
class Unfalsifiable(Exception):
    def __init__(self,hypothesis):
        Exception.__init__(self, "Unable to falsify hypothesis %s"% hypothesis)
