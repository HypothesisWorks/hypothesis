from hypothesis.produce import Producers
from hypothesis.simplify import Simplifiers
from itertools import islice

def assume(condition):
    if not condition: raise UnsatisfiedAssumption()

class Verifier:
    def __init__(self,  simplifiers=None,
                        producers = None,
                        starting_size = 1,
                        warming_rate = 0.05,
                        cooling_rate = 0.01,
                        max_size = 1024,
                        max_failed_runs = 10):
        self.simplifiers = simplifiers or Simplifiers()
        self.producers = producers or Producers()
        self.starting_size = starting_size
        self.warming_rate = warming_rate
        self.cooling_rate = cooling_rate
        self.max_size = max_size
        self.max_failed_runs = max_failed_runs 
                        
    def falsify(self, hypothesis, *argument_types):

        def falsifies(args):
            try:
                return not hypothesis(*args)
            except AssertionError:
                return True
            except UnsatisfiedAssumption:
                return False

        temperature = self.starting_size
        falsifying_example = None

        def look_for_a_falsifying_example(size):
            x = self.producers.produce(argument_types,size)
            if falsifies(x): 
                return x

        while temperature < self.max_size:
            falsifying_example = look_for_a_falsifying_example(int(temperature))
            if falsifying_example:
                break
            temperature *= (1 + self.warming_rate)

        if not falsifying_example: raise Unfalsifiable(hypothesis)

        failed_runs = 0
        while temperature > 1 and failed_runs < self.max_failed_runs:
            new_example = look_for_a_falsifying_example(int(temperature))
            if new_example:
                failed_runs = 0
                falsifying_example = new_example
            else:
                failed_runs += 1

            temperature *= (1 - self.cooling_rate) 
        
        return self.simplifiers.simplify_such_that(falsifying_example, falsifies) 

def falsify(*args, **kwargs):
    return Verifier(**kwargs).falsify(*args)
 
class UnsatisfiedAssumption(Exception):
    def __init__(self):
        Exception.__init__(self, "Unsatisfied assumption")

 
class Unfalsifiable(Exception):
    def __init__(self,hypothesis):
        Exception.__init__(self, "Unable to falsify hypothesis %s"% hypothesis)
