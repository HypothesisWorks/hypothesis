from hypothesis.generate import generator
from hypothesis.minimize import minimize_such_that 
from itertools import islice

def assume(condition):
    if not condition: raise UnsatisfiedAssumption()

def falsify(hypothesis, *argument_types, **kwargs):
    def default_argument(name, value):
        try:
            kwargs[name]
        except KeyError:
            kwargs[name] = value

    default_argument("max_size", 1024)
    default_argument("first_probe_size", 10)
    default_argument("second_probe_size", 50)

    gen = generator(argument_types)

    def falsifies(args):
        try:
            return not hypothesis(*args)
        except AssertionError:
            return True
        except UnsatisfiedAssumption:
            return False

    size = 1
    falsifying_example = None
    while not falsifying_example and size <= kwargs["max_size"]:
        for x in islice(gen(size),kwargs["first_probe_size"]):
            if falsifies(x): 
                falsifying_example = x
                break
        size *= 2

    if not falsifying_example: raise Unfalsifiable(hypothesis)

    while size > 1:
        size /= 2
        for x in islice(gen(size),kwargs["second_probe_size"]):
            if falsifies(x): 
                falsifying_example = x
                break
        else:
            break

    return minimize_such_that(falsifying_example, falsifies) 
  
class UnsatisfiedAssumption(Exception):
    def __init__(self):
        Exception.__init__(self, "Unsatisfied assumption")

 
class Unfalsifiable(Exception):
    def __init__(self,hypothesis):
        Exception.__init__(self, "Unable to falsify hypothesis %s"% hypothesis)
