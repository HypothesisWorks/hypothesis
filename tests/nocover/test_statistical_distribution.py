# coding=utf-8

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# Most of this work is copyright (C) 2013-2015 David R. MacIver
# (david@drmaciver.com), but it contains contributions by other. See
# https://github.com/DRMacIver/hypothesis/blob/master/CONTRIBUTING.rst for a
# full list of people who may hold copyright, and consult the git log if you
# need to determine who owns an individual contribution.

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

# -*- coding: utf-8 -*-
"""Statistical tests over the forms of the distributions in the standard set of
definitions.

These tests all take the form of a classic hypothesis test with the null
hypothesis being that the probability of some event occurring when drawing
data from the distribution produced by some specifier is >= REQUIRED_P

"""

from __future__ import division, print_function, absolute_import, \
    unicode_literals

import re
import math
import random
try:
    from collections import Counter
except ImportError:
    from counter import Counter

import pytest
import hypothesis.internal.reflection as reflection
from hypothesis.strategies import just, sets, lists, floats, tuples, \
    booleans, integers, sampled_from
from hypothesis.internal.compat import hrange
from hypothesis.searchstrategy.strategies import strategy

# We run each individual test at a very high level of significance to the
# point where it will basically only fail if it's really really wildly wrong.
# We then run the Benjamini–Hochberg procedure at the end to detect
# which of these we should consider statistically significant at the 1% level.
REQUIRED_P = 10e-6
FALSE_POSITIVE_RATE = 0.01
MIN_RUNS = 500
MAX_RUNS = MIN_RUNS * 20


if not hasattr(math, 'erf'):
    def erf(x):
        # constants
        a1 =  0.254829592
        a2 = -0.284496736
        a3 =  1.421413741
        a4 = -1.453152027
        a5 =  1.061405429
        p  =  0.3275911

        # Save the sign of x
        sign = 1
        if x < 0:
            sign = -1
        x = abs(x)

        # A & S 7.1.26
        t = 1.0/(1.0 + p*x)
        y = 1.0 - (((((a5*t + a4)*t) + a3)*t + a2)*t + a1)*t*math.exp(-x*x)

        return sign*y

    math.erf = erf


def cumulative_normal(x):
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def cumulative_binomial_probability(n, p, k):
    assert 0 <= k <= n
    assert n > 5
    # Uses a normal approximation because our n is large enough
    mean = float(n) * p
    sd = math.sqrt(n * p * (1 - p))
    assert mean + 3 * sd <= n
    assert mean - 3 * sd >= 0
    return cumulative_normal((k - mean) / sd)


class Result(object):

    def __init__(
        self,
        success_count,
        total_runs,
        desired_probability,
        predicate,
        condition_string,
    ):
        self.success_count = success_count
        self.total_runs = total_runs
        self.desired_probability = desired_probability
        self.predicate = predicate
        self.condition_string = condition_string
        self.p = cumulative_binomial_probability(
            total_runs, self.desired_probability, success_count,
        )
        self.failed = False

    def description(self):
        condition_string = (
            ' | ' + self.condition_string if self.condition_string else '')
        return (
            'P(%s%s) >= %g: p = %g. Occurred in %d / %d = %g of runs. '
        ) % (
            strip_lambda(
                reflection.get_pretty_function_description(self.predicate)),
            condition_string,
            self.desired_probability,
            self.p,
            self.success_count, self.total_runs,
            float(self.success_count) / self.total_runs
        )


def teardown_module(module):
    test_results = []
    for k, v in vars(module).items():
        if 'test_' in k and hasattr(v, 'test_result'):
            test_results.append(v.test_result)
    test_results.sort(key=lambda x: x.p)
    n = len(test_results)
    k = 0
    for i in hrange(n):
        if test_results[i].p < (FALSE_POSITIVE_RATE * (i + 1)) / n:
            k = i + 1
    rejected = [r for r in test_results[:k] if not r.failed]

    if rejected:
        raise HypothesisFalsified(
            ((
                'Although these tests were not significant at p < %g, '
                'the Benjamini-Hochberg procedure demonstrates that the '
                'following are rejected with a false discovery rate of %g: '
                '\n\n'
            ) % (REQUIRED_P, FALSE_POSITIVE_RATE)) + '\n'.join(
                ('  ' + p.description())
                for p in rejected
            ))


INITIAL_LAMBDA = re.compile('^lambda[^:]*:\s*')


def strip_lambda(s):
    return INITIAL_LAMBDA.sub('', s)


class HypothesisFalsified(AssertionError):
    pass


class ConditionTooHard(Exception):
    pass


def define_test(specifier, q, predicate, condition=None):
    def run_test():
        if condition is None:
            _condition = lambda x: True
            condition_string = ''
        else:
            _condition = condition
            condition_string = strip_lambda(
                reflection.get_pretty_function_description(condition))

        count = 0
        successful_runs = 0
        s = strategy(specifier)
        for _ in hrange(MAX_RUNS):
            pv = s.draw_parameter(random)
            x = s.reify(s.draw_template(random, pv))
            if not _condition(x):
                continue
            successful_runs += 1
            if predicate(x):
                count += 1
        if successful_runs < MIN_RUNS:
            raise ConditionTooHard((
                'Unable to find enough examples satisfying predicate %s '
                'only found %d but required at least %d for validity'
            ) % (
                condition_string, successful_runs, MIN_RUNS
            ))

        result = Result(
            count,
            successful_runs,
            q,
            predicate,
            condition_string,
        )

        p = cumulative_binomial_probability(successful_runs, q, count)
        run_test.test_result = result
        # The test passes if we fail to reject the null hypothesis that
        # the probability is at least q
        if p < REQUIRED_P:
            result.failed = True
            raise HypothesisFalsified(result.description() + ' rejected')
    return run_test


def test_assertion_error_message():
    # no really. There's enough code in there that it's silly not to test it.
    # By which I mostly mean "coverage will be sad if I don't".
    # This also guards against my breaking the tests by making it so that they
    # always pass even with implausible predicates.
    with pytest.raises(AssertionError) as e:
        define_test(floats(), 0.5, lambda x: x == 0.0)()
    message = e.value.args[0]
    assert 'x == 0.0' in message
    assert 'lambda' not in message
    assert 'rejected' in message


def test_raises_an_error_on_impossible_conditions():
    with pytest.raises(ConditionTooHard) as e:
        define_test(floats(), 0.5, lambda x: True, condition=lambda x: False)()
    assert 'only found 0 ' in e.value.args[0]


def test_puts_the_condition_in_the_error_message():
    def positive(x):
        return x >= 0

    with pytest.raises(AssertionError) as e:
        define_test(
            floats(), 0.5, lambda x: x == 0.0,
            condition=positive)()
    message = e.value.args[0]
    assert 'x == 0.0' in message
    assert 'lambda not in message'
    assert 'rejected' in message
    assert 'positive' in message


test_can_produce_zero = define_test(integers(), 0.01, lambda x: x == 0)
test_can_produce_large_magnitude_integers = define_test(
    integers(), 0.25, lambda x: abs(x) > 1000
)
test_can_produce_large_positive_integers = define_test(
    integers(), 0.13, lambda x: x > 1000
)
test_can_produce_large_negative_integers = define_test(
    integers(), 0.13, lambda x: x < -1000
)


def long_list(xs):
    return len(xs) >= 20


test_can_produce_positive_infinity = define_test(
    floats(), 0.02, lambda x: x == float('inf')
)

test_can_produce_negative_infinity = define_test(
    floats(), 0.02, lambda x: x == float('-inf')
)

test_can_produce_nan = define_test(
    floats(), 0.02, math.isnan
)

test_can_produce_long_lists_of_positive_integers = define_test(
    lists(integers()), 0.03, lambda x: all(t >= 0 for t in x),
    condition=long_list
)

test_can_produce_long_lists_of_negative_integers = define_test(
    lists(integers()), 0.03, lambda x: all(t <= 0 for t in x),
    condition=lambda x: len(x) >= 20
)

test_can_produce_floats_near_left = define_test(
    floats(0, 1), 0.1,
    lambda t: t < 0.2
)

test_can_produce_floats_near_right = define_test(
    floats(0, 1), 0.1,
    lambda t: t > 0.8
)

test_can_produce_floats_in_middle = define_test(
    floats(0, 1), 0.3,
    lambda t: 0.2 <= t <= 0.8
)

test_can_produce_long_lists = define_test(
    lists(integers()), 0.5, long_list
)

test_can_produce_short_lists = define_test(
    lists(integers()), 0.2, lambda x: len(x) <= 10
)

test_can_produce_lists_bunched_near_left = define_test(
    lists(floats(0, 1)), 0.1,
    lambda ts: all(t < 0.2 for t in ts),
    condition=long_list,
)

test_can_produce_lists_bunched_near_right = define_test(
    lists(floats(0, 1)), 0.1,
    lambda ts: all(t > 0.8 for t in ts),
    condition=long_list,
)

test_can_produce_the_same_int_twice = define_test(
    tuples(lists(integers()), integers()), 0.01,
    lambda t: len([x for x in t[0] if x == t[1]]) > 1
)


def distorted_value(x):
    c = Counter(x)
    return min(c.values()) * 3 <= max(c.values())


def distorted(x):
    return distorted_value(map(type, x))


test_sampled_from_large_number_usually_mixes_some = define_test(
    lists(sampled_from(range(50))), 0.5, lambda x: len(set(x)) >= 25,
    condition=lambda t: len(t) >= 50,
)


test_sampled_from_usually_distorted = define_test(
    lists(sampled_from(range(5))), 0.5, distorted_value,
    condition=lambda x: len(x) >= 3,
)


test_non_empty_subset_of_two_is_usually_large = define_test(
    sets(sampled_from((1, 2))), 0.6,
    lambda t: len(t) == 2
)

test_mostly_sensible_floats = define_test(
    floats(), 0.5,
    lambda t: t + 1 > t
)

test_mostly_largish_floats = define_test(
    floats(), 0.5,
    lambda t: t + 1 > 1,
    condition=lambda x: x > 0,
)

test_ints_can_occasionally_be_really_large = define_test(
    integers(), 0.01,
    lambda t: t >= 2 ** 63
)

test_mixing_is_sometimes_distorted = define_test(
    lists(booleans() | tuples()), 0.25, distorted,
    condition=lambda x: len(set(map(type, x))) == 2,
)

test_mixes_2_reasonably_often = define_test(
    lists(booleans() | tuples()), 0.25, lambda x: len(set(map(type, x))) > 1,
    condition=bool,
)

test_partial_mixes_3_reasonably_often = define_test(
    lists(booleans() | tuples() | just('hi')), 0.15,
    lambda x: 1 < len(set(map(type, x))) < 3,
    condition=bool,
)

test_mixes_not_too_often = define_test(
    lists(booleans() | tuples()), 0.1, lambda x: len(set(map(type, x))) == 1,
    condition=bool,
)
