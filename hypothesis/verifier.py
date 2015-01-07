from hypothesis.searchstrategy import SearchStrategies
from random import Random
import time


def assume(condition):
    if not condition:
        raise UnsatisfiedAssumption()


class Verifier(object):

    def __init__(self,
                 search_strategies=None,
                 min_satisfying_examples=5,
                 max_examples=100,
                 max_falsifying_examples=5,
                 max_runs_per_parameter_value=5,
                 max_unsatisfied_per_parameter_value=2,
                 timeout=60, random=None):
        self.search_strategies = search_strategies or SearchStrategies()
        self.min_satisfying_examples = min_satisfying_examples
        self.max_falsifying_examples = max_falsifying_examples
        self.max_examples = max_examples
        self.max_runs_per_parameter_value = max_runs_per_parameter_value
        self.max_unsatisfied_per_parameter_value = (
            max_unsatisfied_per_parameter_value)
        self.timeout = timeout
        self.start_time = time.time()
        self.random = random or Random()

    def time_to_call_it_a_day(self):
        return time.time() > self.start_time + self.timeout

    def falsify(self, hypothesis, *argument_types):
        search_strategy = (self.search_strategies
                               .specification_for(argument_types))

        def falsifies(args):
            try:
                return not hypothesis(*args)
            except AssertionError:
                return True
            except UnsatisfiedAssumption:
                return False

        falsifying_examples = []
        examples_found = 0
        satisfying_examples = 0
        timed_out = False

        pv = search_strategy.parameter.draw(self.random)
        runs_with_value = 0
        unsatisfied_with_value = 0
        while not (
            examples_found >= self.max_examples or
            len(falsifying_examples) >= self.max_falsifying_examples
        ):
            if self.time_to_call_it_a_day():
                timed_out = True
                break
            if (
                runs_with_value >= self.max_runs_per_parameter_value or
                unsatisfied_with_value >=
                self.max_unsatisfied_per_parameter_value
            ):
                pv = search_strategy.parameter.draw(self.random)
                runs_with_value = 0
                unsatisfied_with_value = 0
            else:
                runs_with_value += 1
            args = search_strategy.produce(self.random, pv)
            examples_found += 1
            try:
                is_falsifying_example = not hypothesis(*args)
            except AssertionError:
                is_falsifying_example = True
            except UnsatisfiedAssumption:
                unsatisfied_with_value += 1
                continue
            satisfying_examples += 1
            if is_falsifying_example:
                falsifying_examples.append(args)

        if not falsifying_examples:
            if satisfying_examples < self.min_satisfying_examples:
                raise Unsatisfiable(hypothesis, examples_found)
            elif timed_out:
                raise Timeout(hypothesis, self.timeout)
            else:
                raise Unfalsifiable(hypothesis)

        best_example = min(falsifying_examples, key=search_strategy.complexity)

        for t in search_strategy.simplify_such_that(best_example, falsifies):
            best_example = t
            if self.time_to_call_it_a_day():
                break

        return best_example


def falsify(*args, **kwargs):
    return Verifier(**kwargs).falsify(*args)


class HypothesisException(Exception):
    pass


class UnsatisfiedAssumption(HypothesisException):

    def __init__(self):
        super(UnsatisfiedAssumption, self).__init__('Unsatisfied assumption')


class Unfalsifiable(HypothesisException):

    def __init__(self, hypothesis, extra=''):
        super(Unfalsifiable, self).__init__(
            'Unable to falsify hypothesis %s%s' % (hypothesis, extra)
        )


class Unsatisfiable(HypothesisException):

    def __init__(self, hypothesis, examples):
        super(Unsatisfiable, self).__init__(
            ('Unable to satisfy assumptions of hypothesis %s. ' +
             'Only %s examples found ') % (hypothesis, str(examples)))


class Timeout(Unfalsifiable):

    def __init__(self, hypothesis, timeout):
        super(Timeout, self).__init__(
            hypothesis,
            ' after %.2fs' % (timeout,)
        )
