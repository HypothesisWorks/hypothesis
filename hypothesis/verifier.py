from hypothesis.produce import Producers
from hypothesis.simplify import Simplifiers
from itertools import islice

def assume(condition):
    if not condition: raise UnsatisfiedAssumption()

class Verifier:
    def __init__(self,  simplifiers=None,
                        producers = None,
                        starting_size = 1,
                        first_probe_size=10,
                        second_probe_size = 50,
                        max_size = 1024):
        self.simplifiers = simplifiers or Simplifiers()
        self.producers = producers or Producers()
        self.starting_size = starting_size
        self.first_probe_size = first_probe_size
        self.second_probe_size = second_probe_size
        self.max_size = max_size
                        
    def falsify(self, hypothesis, *argument_types):
        gen = self.producers.producer(argument_types)

        def falsifies(args):
            try:
                return not hypothesis(*args)
            except AssertionError:
                return True
            except UnsatisfiedAssumption:
                return False

        size = self.starting_size
        falsifying_example = None
        while not falsifying_example and size <= self.max_size:
            for _ in xrange(self.first_probe_size):
                x = gen(self.producers,size)
                if falsifies(x): 
                    falsifying_example = x
                    break
            size *= 2

        if not falsifying_example: raise Unfalsifiable(hypothesis)

        while size > 1:
            size /= 2
            for _ in xrange(self.second_probe_size):
                x = gen(self.producers,size)
                if falsifies(x): 
                    falsifying_example = x
                    break
            else:
                break

        return self.simplifiers.simplify_such_that(falsifying_example, falsifies) 

def falsify(*args, **kwargs):
    return Verifier(**kwargs).falsify(*args)
 
class UnsatisfiedAssumption(Exception):
    def __init__(self):
        Exception.__init__(self, "Unsatisfied assumption")

 
class Unfalsifiable(Exception):
    def __init__(self,hypothesis):
        Exception.__init__(self, "Unable to falsify hypothesis %s"% hypothesis)
