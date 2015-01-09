from hypothesis.strategytable import SearchStrategies
from random import Random
import time
from six.moves import xrange
import hypothesis.settings as hs


def assume(condition):
    if not condition:
        raise UnsatisfiedAssumption()


class Verifier(object):
    def __init__(
        self,
        search_strategies=None,
        random=None,
        settings=None,
    ):
        if settings is None:
            settings = hs.default
        self.search_strategies = search_strategies or SearchStrategies()
        self.min_satisfying_examples = settings.min_satisfying_examples
        self.max_falsifying_examples = settings.max_falsifying_examples
        self.n_parameter_values = int(float(settings.max_examples) / 10) + 1
        self.max_examples = settings.max_examples
        self.timeout = settings.timeout
        self.random = random or Random()

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

        parameter_values = [
            search_strategy.parameter.draw(self.random)
            for _ in xrange(self.n_parameter_values)
        ]

        accepted_examples = [0] * self.n_parameter_values
        rejected_examples = [0] * self.n_parameter_values

        start_time = time.time()

        def time_to_call_it_a_day():
            return time.time() >= start_time + self.timeout

        initial_run = 0

        while not (
            examples_found >= self.max_examples or
            len(falsifying_examples) >= self.max_falsifying_examples
        ):
            if time_to_call_it_a_day():
                timed_out = True
                break

            if initial_run < len(parameter_values):
                i = initial_run
                initial_run += 1
            else:
                i = max(
                    xrange(len(parameter_values)),
                    key=lambda k: self.random.betavariate(
                        accepted_examples[k] + 1, rejected_examples[k] + 1
                    )
                )
            pv = parameter_values[i]

            args = search_strategy.produce(self.random, pv)
            examples_found += 1
            try:
                is_falsifying_example = not hypothesis(*args)
            except AssertionError:
                is_falsifying_example = True
            except UnsatisfiedAssumption:
                rejected_examples[i] += 1
                continue
            accepted_examples[i] += 1
            satisfying_examples += 1
            if is_falsifying_example:
                falsifying_examples.append(args)

        if not falsifying_examples:
            if satisfying_examples < self.min_satisfying_examples:
                raise Unsatisfiable(hypothesis, satisfying_examples)
            elif timed_out:
                raise Timeout(hypothesis, self.timeout)
            else:
                raise Unfalsifiable(hypothesis)

        for x in falsifying_examples:
            if not falsifies(x):
                raise Flaky(hypothesis, x)

        best_example = min(falsifying_examples, key=search_strategy.complexity)

        for t in search_strategy.simplify_such_that(best_example, falsifies):
            best_example = t
            if time_to_call_it_a_day():
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


class Flaky(HypothesisException):
    def __init__(self, hypothesis, example):
        super(Flaky, self).__init__((
            "Hypothesis %r produces unreliable results: %r falsified it on the"
            " first call but did not on a subsequent one"
        ) % (hypothesis, example))


class Timeout(Unfalsifiable):

    def __init__(self, hypothesis, timeout):
        super(Timeout, self).__init__(
            hypothesis,
            ' after %.2fs' % (timeout,)
        )
