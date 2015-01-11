"""
Statistical tests over the forms of the distributions in the standard set of
definitions.

These tests all take the form of a classic hypothesis test with the null
hypothesis being that the probability of some event occurring when drawing
data from the distribution produced by some descriptor is >= REQUIRED_P
"""

import math
import hypothesis.internal.utils.reflection as reflection
import random
from hypothesis.strategytable import StrategyTable
import hypothesis.descriptors as descriptors
from six.moves import xrange
import re
import pytest

REQUIRED_P = 10e-3
MIN_RUNS = 500
MAX_RUNS = MIN_RUNS * 20


def cumulative_normal(x):
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def cumulative_binomial_probability(n, p, k):
    assert n > 5
    # Uses a normal approximation because our n is large enough
    mean = float(n) * p
    sd = math.sqrt(n * p * (1 - p))
    assert mean + 3 * sd <= n
    assert mean - 3 * sd >= 0
    return cumulative_normal((k - mean) / sd)


INITIAL_LAMBDA = re.compile("^lambda[^:]*:\s*")


def strip_lambda(s):
    return INITIAL_LAMBDA.sub("", s)


class HypothesisFalsified(AssertionError):
    pass


class ConditionTooHard(Exception):
    pass


def define_test(descriptor, q, predicate, condition=None):
    def run_test():
        if condition is None:
            condition_string = ""
            _condition = lambda x: True
        else:
            condition_string = strip_lambda(
                reflection.get_pretty_function_description(condition))
            _condition = condition

        count = 0
        successful_runs = 0
        strategy = StrategyTable.default().strategy(descriptor)
        for _ in xrange(MAX_RUNS):
            pv = strategy.parameter.draw(random)
            x = strategy.produce(random, pv)
            if not _condition(x):
                continue
            successful_runs += 1
            if predicate(x):
                count += 1
        if successful_runs < MIN_RUNS:
            raise ConditionTooHard((
                "Unable to find enough examples satisfying predicate %s "
                "only found %d but required at least %d for validity"
            ) % (
                condition_string, successful_runs, MIN_RUNS
            ))

        p = cumulative_binomial_probability(successful_runs, q, count)
        # The test passes if we fail to reject the null hypothesis that
        # the probability is at least q
        if p < REQUIRED_P:
            conditional = " | " + condition_string if condition_string else ""

            raise HypothesisFalsified((
                "p = %g < %g. Occurred in %d / %d = %g of runs. "
                "Hypothesis that P(%s%s) >= %f rejected"
                ) % (
                    p, REQUIRED_P, count, successful_runs,
                    float(count) / successful_runs,
                    INITIAL_LAMBDA.sub(
                        "",
                        reflection.get_pretty_function_description(predicate)),
                    conditional,
                    q
                )
            )
    return run_test


def test_assertion_error_message():
    # no really. There's enough code in there that it's silly not to test it.
    # By which I mostly mean "coverage will be sad if I don't".
    # This also guards against my breaking the tests by making it so that they
    # always pass even with implausible predicates.
    with pytest.raises(AssertionError) as e:
        define_test(float, 0.5, lambda x: x == 0.0)()
    message = e.value.args[0]
    assert 'x == 0.0' in message
    assert 'lambda not in message'
    assert 'rejected' in message


def test_raises_an_error_on_impossible_conditions():
    with pytest.raises(ConditionTooHard) as e:
        define_test(float, 0.5, lambda x: True, condition=lambda x: False)()
    assert "only found 0 " in e.value.args[0]


def test_puts_the_condition_in_the_error_message():
    def positive(x):
        return x >= 0

    with pytest.raises(AssertionError) as e:
        define_test(
            float, 0.5, lambda x: x == 0.0,
            condition=positive)()
    message = e.value.args[0]
    assert 'x == 0.0' in message
    assert 'lambda not in message'
    assert 'rejected' in message
    assert 'positive' in message


test_can_produce_zero = define_test(int, 0.01, lambda x: x == 0)
test_can_produce_large_magnitude_integers = define_test(
    int, 0.1, lambda x: abs(x) > 1000
)
test_can_produce_large_positive_integers = define_test(
    int, 0.05, lambda x: x > 1000
)
test_can_produce_large_negative_integers = define_test(
    int, 0.05, lambda x: x < -1000
)


def long_list(xs):
    return len(xs) >= 20


test_can_produce_long_lists_of_positive_integers = define_test(
    [int], 0.01, lambda x: all(t >= 0 for t in x),
    condition=long_list
)

test_can_produce_long_lists_of_negative_integers = define_test(
    [int], 0.01, lambda x: all(t <= 0 for t in x),
    condition=lambda x: len(x) >= 20
)

test_can_produce_floats_near_left = define_test(
    descriptors.floats_in_range(0, 1), 0.01,
    lambda t: t < 0.05
)

test_can_produce_floats_near_right = define_test(
    descriptors.floats_in_range(0, 1), 0.01,
    lambda t: t > 0.95
)

test_can_produce_floats_in_middle = define_test(
    descriptors.floats_in_range(0, 1), 0.25,
    lambda t: 0.2 <= t <= 0.8
)

test_can_produce_long_lists = define_test(
    [int], 0.05, lambda xs: long_list
)

test_can_produce_lists_bunched_near_left = define_test(
    [descriptors.floats_in_range(0, 1)], 0.001,
    lambda ts: len(ts) >= 20 and all(t < 0.02 for t in ts)
)

test_can_produce_lists_bunched_near_right = define_test(
    [descriptors.floats_in_range(0, 1)], 0.001,
    lambda ts: len(ts) >= 20 and all(t > 0.98 for t in ts)
)
