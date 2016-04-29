# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2015 David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
# CONTRIBUTING.rst for a full list of people who may hold copyright, and
# consult the git log if you need to determine who owns an individual
# contribution.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.
#
# END HEADER

# -*- coding: utf-8 -*-
"""Statistical tests over the forms of the distributions in the standard set of
definitions.

These tests all take the form of a classic hypothesis test with the null
hypothesis being that the probability of some event occurring when drawing
data from the distribution produced by some specifier is >= REQUIRED_P

"""


from __future__ import division, print_function, absolute_import

import re
import math
import collections

import pytest

import hypothesis.internal.reflection as reflection
from hypothesis import settings as Settings
from hypothesis.errors import UnsatisfiedAssumption
from hypothesis.strategies import just, sets, text, lists, floats, \
    tuples, booleans, integers, sampled_from
from hypothesis.internal.compat import PY26, hrange
from hypothesis.internal.conjecture.engine import \
    TestRunner as ConTestRunner

pytestmark = pytest.mark.skipif(PY26, reason=u'2.6 lacks erf')

# We run each individual test at a very high level of significance to the
# point where it will basically only fail if it's really really wildly wrong.
# We then run the Benjamini–Hochberg procedure at the end to detect
# which of these we should consider statistically significant at the 1% level.
REQUIRED_P = 10e-6
FALSE_POSITIVE_RATE = 0.01
MIN_RUNS = 500
MAX_RUNS = MIN_RUNS * 20


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
        specifier,
    ):
        self.success_count = success_count
        self.total_runs = total_runs
        self.desired_probability = desired_probability
        self.predicate = predicate
        self.condition_string = condition_string
        self.p = cumulative_binomial_probability(
            total_runs, self.desired_probability, success_count,
        )
        self.specifier = specifier
        self.failed = False

    def description(self):
        condition_string = (
            ' | ' + self.condition_string if self.condition_string else u'')
        return (
            'P(%s%s) >= %g given %r: p = %g.'
            ' Occurred in %d / %d = %g of runs. '
        ) % (
            strip_lambda(
                reflection.get_pretty_function_description(self.predicate)),
            condition_string,
            self.desired_probability,
            self.specifier,
            self.p,
            self.success_count, self.total_runs,
            float(self.success_count) / self.total_runs
        )


def teardown_module(module):
    test_results = []
    for k, v in vars(module).items():
        if u'test_' in k and hasattr(v, u'test_result'):
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
                u'Although these tests were not significant at p < %g, '
                u'the Benjamini-Hochberg procedure demonstrates that the '
                u'following are rejected with a false discovery rate of %g: '
                u'\n\n'
            ) % (REQUIRED_P, FALSE_POSITIVE_RATE)) + u'\n'.join(
                (u'  ' + p.description())
                for p in rejected
            ))


INITIAL_LAMBDA = re.compile(u'^lambda[^:]*:\s*')


def strip_lambda(s):
    return INITIAL_LAMBDA.sub(u'', s)


class HypothesisFalsified(AssertionError):
    pass


class ConditionTooHard(Exception):
    pass


def define_test(specifier, q, predicate, condition=None):
    def run_test():
        if condition is None:
            def _condition(x):
                return True
            condition_string = u''
        else:
            _condition = condition
            condition_string = strip_lambda(
                reflection.get_pretty_function_description(condition))

        count = [0]
        successful_runs = [0]

        def test_function(data):
            try:
                value = data.draw(specifier)
            except UnsatisfiedAssumption:
                data.mark_invalid()
            if not _condition(value):
                data.mark_invalid()
            successful_runs[0] += 1
            if predicate(value):
                count[0] += 1
        ConTestRunner(
            test_function,
            settings=Settings(
                max_examples=MAX_RUNS,
                max_iterations=MAX_RUNS * 10,
            )).run()
        successful_runs = successful_runs[0]
        count = count[0]
        if successful_runs < MIN_RUNS:
            raise ConditionTooHard((
                u'Unable to find enough examples satisfying predicate %s '
                u'only found %d but required at least %d for validity'
            ) % (
                condition_string, successful_runs, MIN_RUNS
            ))

        result = Result(
            count,
            successful_runs,
            q,
            predicate,
            condition_string,
            specifier,
        )

        p = cumulative_binomial_probability(successful_runs, q, count)
        run_test.test_result = result
        # The test passes if we fail to reject the null hypothesis that
        # the probability is at least q
        if p < REQUIRED_P:
            result.failed = True
            raise HypothesisFalsified(result.description() + u' rejected')
    return run_test


def test_assertion_error_message():
    # no really. There's enough code in there that it's silly not to test it.
    # By which I mostly mean "coverage will be sad if I don't".
    # This also guards against my breaking the tests by making it so that they
    # always pass even with implausible predicates.
    with pytest.raises(AssertionError) as e:
        define_test(floats(), 0.5, lambda x: x == 0.0)()
    message = e.value.args[0]
    assert u'x == 0.0' in message
    assert u'lambda' not in message
    assert u'rejected' in message


def test_raises_an_error_on_impossible_conditions():
    with pytest.raises(ConditionTooHard) as e:
        define_test(floats(), 0.5, lambda x: True, condition=lambda x: False)()
    assert u'only found 0 ' in e.value.args[0]


def test_puts_the_condition_in_the_error_message():
    def positive(x):
        return x >= 0

    with pytest.raises(AssertionError) as e:
        define_test(
            floats(), 0.5, lambda x: x == 0.0,
            condition=positive)()
    message = e.value.args[0]
    assert u'x == 0.0' in message
    assert u'lambda not in message'
    assert u'rejected' in message
    assert u'positive' in message


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


test_can_produce_unstripped_strings = define_test(
    text(), 0.05, lambda x: x != x.strip()
)

test_can_produce_stripped_strings = define_test(
    text(), 0.05, lambda x: x == x.strip()
)

test_can_produce_multi_line_strings = define_test(
    text(average_size=25.0), 0.1, lambda x: u'\n' in x
)

test_can_produce_ascii_strings = define_test(
    text(), 0.1, lambda x: all(ord(c) <= 127 for c in x),
)

test_can_produce_long_strings_with_no_ascii = define_test(
    text(), 0.02, lambda x: all(ord(c) > 127 for c in x),
    condition=lambda x: len(x) >= 10
)

test_can_produce_short_strings_with_some_non_ascii = define_test(
    text(), 0.1, lambda x: any(ord(c) > 127 for c in x),
    condition=lambda x: len(x) <= 3
)

test_can_produce_positive_infinity = define_test(
    floats(), 0.01, lambda x: x == float(u'inf')
)

test_can_produce_negative_infinity = define_test(
    floats(), 0.01, lambda x: x == float(u'-inf')
)

test_can_produce_nan = define_test(
    floats(), 0.02, math.isnan
)

test_can_produce_long_lists_of_negative_integers = define_test(
    lists(integers()), 0.005, lambda x: all(t <= 0 for t in x),
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
    lists(integers(), average_size=25.0), 0.2, long_list
)

test_can_produce_short_lists = define_test(
    lists(integers()), 0.2, lambda x: len(x) <= 10
)

test_can_produce_the_same_int_twice = define_test(
    tuples(lists(integers(), average_size=25.0), integers()), 0.01,
    lambda t: t[0].count(t[1]) > 1
)


def distorted_value(x):
    c = collections.Counter(x)
    return min(c.values()) * 3 <= max(c.values())


def distorted(x):
    return distorted_value(map(type, x))


test_sampled_from_large_number_can_mix = define_test(
    lists(sampled_from(range(50)), min_size=50), 0.1,
    lambda x: len(set(x)) >= 25,
)


test_sampled_from_often_distorted = define_test(
    lists(sampled_from(range(5))), 0.28, distorted_value,
    condition=lambda x: len(x) >= 3,
)


test_non_empty_subset_of_two_is_usually_large = define_test(
    sets(sampled_from((1, 2))), 0.1,
    lambda t: len(t) == 2
)

test_subset_of_ten_is_sometimes_empty = define_test(
    sets(integers(1, 10)), 0.05, lambda t: len(t) == 0
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
    lists(booleans() | tuples(), average_size=25.0), 0.05, distorted,
    condition=lambda x: len(set(map(type, x))) == 2,
)

test_mixes_2_reasonably_often = define_test(
    lists(booleans() | tuples(), average_size=25.0), 0.15,
    lambda x: len(set(map(type, x))) > 1,
    condition=bool,
)

test_partial_mixes_3_reasonably_often = define_test(
    lists(booleans() | tuples() | just(u'hi'), average_size=25.0), 0.10,
    lambda x: 1 < len(set(map(type, x))) < 3,
    condition=bool,
)

test_mixes_not_too_often = define_test(
    lists(booleans() | tuples(), average_size=25.0), 0.1,
    lambda x: len(set(map(type, x))) == 1,
    condition=bool,
)

test_float_lists_have_non_reversible_sum = define_test(
    lists(floats(), min_size=2), 0.01, lambda x: sum(x) != sum(reversed(x)),
    condition=lambda x: not math.isnan(sum(x))
)
