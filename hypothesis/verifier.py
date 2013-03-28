from hypothesis.searchstrategy import SearchStrategies
from hypothesis.flags import Flags
from random import random

def assume(condition):
    if not condition: raise UnsatisfiedAssumption()

class Verifier(object):
    def __init__(self,  search_strategies=None,
                        starting_size = 1.0,
                        warming_rate = 0.5,
                        cooling_rate = 0.1,
                        runs_to_explore_flags = 3,
                        min_satisfying_examples = 5,
                        max_size = 512,
                        max_failed_runs = 10):
        self.search_strategies = search_strategies or SearchStrategies()
        self.min_satisfying_examples = min_satisfying_examples
        self.starting_size = starting_size
        self.warming_rate = warming_rate
        self.cooling_rate = cooling_rate
        self.max_size = max_size
        self.max_failed_runs = max_failed_runs
        self.runs_to_explore_flags = runs_to_explore_flags 
                        
    def falsify(self, hypothesis, *argument_types):
        search_strategy = self.search_strategies.specification_for(argument_types)
        flags = None
        # TODO: This is a sign that I should be pulling some of this out into
        # an object.
        examples_found = [0]

        def falsifies(args):
            try:
                examples_found[0] += 1
                return not hypothesis(*args)
            except AssertionError:
                return True
            except UnsatisfiedAssumption:
                examples_found[0] -= 1
                return False

        temperature = self.starting_size
        falsifying_examples = []

        def look_for_a_falsifying_example(size):
            x = search_strategy.produce(size, flags)

            if falsifies(x): 
                falsifying_examples.append(x)
                return True
            else:
                return False

        while temperature < self.max_size:
            rtf = self.runs_to_explore_flags
            for i in xrange(self.runs_to_explore_flags):
                # Try a number of degrees of turning flags on, spaced evenly but
                # with the lowest probability of a flag being on being > 0 and 
                # the highest < 1
                # Note that as soon as we find a falsifying example with a set of
                # flags, those are the flags we'll be using for the rest of the
                # run
                p = float(i + 1)/(rtf + 1)
                def generate_flags():
                    return Flags([x for x in search_strategy.flags().flags if random() <= p])
                flags = generate_flags() 
                look_for_a_falsifying_example(temperature)
                if falsifying_examples:
                    break
            if falsifying_examples:
                    break
            temperature += self.warming_rate

        if not falsifying_examples:
            ef = examples_found[0]
            if ef < self.min_satisfying_examples:
                raise Unsatisfiable(hypothesis, ef)
            else:
                raise Unfalsifiable(hypothesis)

        failed_runs = 0
        while temperature > 1 and failed_runs < self.max_failed_runs:
            if not look_for_a_falsifying_example(temperature):
                failed_runs += 1

            temperature -= self.cooling_rate
      
        best_example = min(falsifying_examples, key=search_strategy.complexity)

        return search_strategy.simplify_such_that(best_example, falsifies) 

def falsify(*args, **kwargs):
    return Verifier(**kwargs).falsify(*args)
 
class UnsatisfiedAssumption(Exception):
    def __init__(self):
        Exception.__init__(self, "Unsatisfied assumption")

 
class Unfalsifiable(Exception):
    def __init__(self,hypothesis):
        Exception.__init__(self, "Unable to falsify hypothesis %s"% hypothesis)

class Unsatisfiable(Exception):
    def __init__(self,hypothesis, examples):
        Exception.__init__(self, "Unable to satisfy assumptions of hypothesis %s. Only %s examples found "% (hypothesis, str(examples)))
