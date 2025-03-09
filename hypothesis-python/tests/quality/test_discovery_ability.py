# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

# -*- coding: utf-8 -*-
"""Statistical tests over the forms of the distributions in the standard set of
definitions.

These tests all take the form of a classic hypothesis test with the null
hypothesis being that the probability of some event occurring when
drawing data from the distribution produced by some specifier is >=
REQUIRED_P
"""

import collections
import math
import re

from hypothesis import HealthCheck, settings as Settings
from hypothesis.control import BuildContext
from hypothesis.errors import UnsatisfiedAssumption
from hypothesis.internal import reflection
from hypothesis.internal.conjecture.engine import ConjectureRunner
from hypothesis.strategies import (
    binary,
    booleans,
    floats,
    integers,
    just,
    lists,
    one_of,
    sampled_from,
    sets,
    text,
    tuples,
)

from tests.common.utils import no_shrink

RUNS = 100


INITIAL_LAMBDA = re.compile("^lambda[^:]*:\\s*")


def strip_lambda(s):
    return INITIAL_LAMBDA.sub("", s)


class HypothesisFalsified(AssertionError):
    pass


def define_test(specifier, predicate, condition=None, p=0.5, suppress_health_check=()):
    required_runs = int(RUNS * p)

    def run_test():
        if condition is None:

            def _condition(x):
                return True

            condition_string = ""
        else:
            _condition = condition
            condition_string = strip_lambda(
                reflection.get_pretty_function_description(condition)
            )

        def test_function(data):
            with BuildContext(data):
                try:
                    value = data.draw(specifier)
                except UnsatisfiedAssumption:
                    data.mark_invalid()
                if not _condition(value):
                    data.mark_invalid()
                if predicate(value):
                    data.mark_interesting()

        successes = 0
        actual_runs = 0
        for actual_runs in range(1, RUNS + 1):
            # We choose the max_examples a bit larger than default so that we
            # run at least 100 examples outside of the small example generation
            # part of the generation phase.
            runner = ConjectureRunner(
                test_function,
                settings=Settings(
                    max_examples=150,
                    phases=no_shrink,
                    suppress_health_check=suppress_health_check,
                ),
            )
            runner.run()
            if runner.interesting_examples:
                successes += 1
                if successes >= required_runs:
                    return

            # If we reach a point where it's impossible to hit our target even
            # if every remaining attempt were to succeed, give up early and
            # report failure.
            if (required_runs - successes) > (RUNS - actual_runs):
                break

        event = reflection.get_pretty_function_description(predicate)
        if condition is not None:
            event += "|"
            event += condition_string

        raise HypothesisFalsified(
            f"P({event}) ~ {successes} / {actual_runs} = "
            f"{successes / actual_runs:.2f} < {required_runs / RUNS:.2f}; "
            "rejected"
        )

    return run_test


test_can_produce_zero = define_test(integers(), lambda x: x == 0)
test_can_produce_large_magnitude_integers = define_test(
    integers(), lambda x: abs(x) > 1000
)
test_can_produce_large_positive_integers = define_test(integers(), lambda x: x > 1000)
test_can_produce_large_negative_integers = define_test(integers(), lambda x: x < -1000)


def long_list(xs):
    return len(xs) >= 10


test_can_produce_unstripped_strings = define_test(text(), lambda x: x != x.strip())

test_can_produce_stripped_strings = define_test(text(), lambda x: x == x.strip())

# The pass probability here was previously 0.5, but some intermediate changes
# while working on the ir tweaked the distribution and made it flaky. We can
# reevaluate this once things have settled down, and likely bump the pass
# probability back up.
test_can_produce_multi_line_strings = define_test(text(), lambda x: "\n" in x, p=0.35)

test_can_produce_ascii_strings = define_test(
    text(), lambda x: all(ord(c) <= 127 for c in x)
)

test_can_produce_long_strings_with_no_ascii = define_test(
    text(min_size=5), lambda x: all(ord(c) > 127 for c in x), p=0.1
)

test_can_produce_short_strings_with_some_non_ascii = define_test(
    text(), lambda x: any(ord(c) > 127 for c in x), condition=lambda x: len(x) <= 3
)

test_can_produce_large_binary_strings = define_test(
    binary(), lambda x: len(x) > 10, p=0.3
)

test_can_produce_positive_infinity = define_test(floats(), lambda x: x == math.inf)

test_can_produce_negative_infinity = define_test(floats(), lambda x: x == -math.inf)

test_can_produce_nan = define_test(floats(), math.isnan)

test_can_produce_floats_near_left = define_test(floats(0, 1), lambda t: t < 0.2)

test_can_produce_floats_near_right = define_test(floats(0, 1), lambda t: t > 0.8)

test_can_produce_floats_in_middle = define_test(floats(0, 1), lambda t: 0.2 <= t <= 0.8)

test_can_produce_long_lists = define_test(lists(integers()), long_list, p=0.3)

test_can_produce_short_lists = define_test(lists(integers()), lambda x: len(x) <= 10)

test_can_produce_the_same_int_twice = define_test(
    lists(integers()), lambda t: len(set(t)) < len(t)
)


def distorted_value(x):
    c = collections.Counter(x)
    return min(c.values()) * 3 <= max(c.values())


def distorted(x):
    return distorted_value(map(type, x))


test_sampled_from_large_number_can_mix = define_test(
    lists(sampled_from(range(50)), min_size=50), lambda x: len(set(x)) >= 25
)


test_sampled_from_often_distorted = define_test(
    lists(sampled_from(range(5))), distorted_value, condition=lambda x: len(x) >= 3
)


test_non_empty_subset_of_two_is_usually_large = define_test(
    sets(sampled_from((1, 2))), lambda t: len(t) == 2
)

test_subset_of_ten_is_sometimes_empty = define_test(
    sets(integers(1, 10)), lambda t: len(t) == 0
)

test_mostly_sensible_floats = define_test(floats(), lambda t: t + 1 > t)

test_mostly_largish_floats = define_test(
    floats(), lambda t: t + 1 > 1, condition=lambda x: x > 0
)

test_ints_can_occasionally_be_really_large = define_test(
    integers(), lambda t: t >= 2**63
)

test_mixing_is_sometimes_distorted = define_test(
    lists(booleans() | tuples()),
    distorted,
    condition=lambda x: len(set(map(type, x))) == 2,
    suppress_health_check=[HealthCheck.filter_too_much],
)

test_mixes_2_reasonably_often = define_test(
    lists(booleans() | tuples()), lambda x: len(set(map(type, x))) > 1, condition=bool
)

test_partial_mixes_3_reasonably_often = define_test(
    lists(booleans() | tuples() | just("hi")),
    lambda x: 1 < len(set(map(type, x))) < 3,
    condition=bool,
)

test_mixes_not_too_often = define_test(
    lists(booleans() | tuples()), lambda x: len(set(map(type, x))) == 1, condition=bool
)

test_integers_are_usually_non_zero = define_test(integers(), lambda x: x != 0)

test_integers_are_sometimes_zero = define_test(integers(), lambda x: x == 0)

test_integers_are_often_small = define_test(integers(), lambda x: abs(x) <= 100)


test_integers_are_often_small_but_not_that_small = define_test(
    integers(), lambda x: 50 <= abs(x) <= 255
)


# This series of tests checks that the one_of() strategy flattens branches
# correctly.  We assert that the probability of any branch is >= 0.1,
# approximately (1/8 = 0.125), regardless of how heavily nested it is in the
# strategy.

# This first strategy chooses an integer between 0 and 7 (inclusive).
one_of_nested_strategy = one_of(
    just(0),
    one_of(
        just(1), just(2), one_of(just(3), just(4), one_of(just(5), just(6), just(7)))
    ),
)

for i in range(8):
    exec(
        f"""test_one_of_flattens_branches_{i} = define_test(
        one_of_nested_strategy, lambda x: x == {i}
    )"""
    )


xor_nested_strategy = just(0) | (
    just(1) | just(2) | (just(3) | just(4) | (just(5) | just(6) | just(7)))
)

for i in range(8):
    exec(
        f"""test_xor_flattens_branches_{i} = define_test(
        xor_nested_strategy, lambda x: x == {i}
    )"""
    )


# This strategy tests interactions with `map()`.  They generate integers
# from the set {1, 4, 6, 16, 20, 24, 28, 32}.
def double(x):
    return x * 2


one_of_nested_strategy_with_map = one_of(
    just(1),
    one_of(
        (just(2) | just(3)).map(double),
        one_of(
            (just(4) | just(5)).map(double),
            one_of((just(6) | just(7) | just(8)).map(double)),
        ).map(double),
    ),
)

for i in (1, 4, 6, 16, 20, 24, 28, 32):
    exec(
        f"""test_one_of_flattens_map_branches_{i} = define_test(
        one_of_nested_strategy_with_map, lambda x: x == {i}
    )"""
    )


# This strategy tests interactions with `flatmap()`.  It generates lists
# of length 0-7 (inclusive) in which every element is `None`.
one_of_nested_strategy_with_flatmap = just(None).flatmap(
    lambda x: one_of(
        just([x] * 0),
        just([x] * 1),
        one_of(
            just([x] * 2),
            just([x] * 3),
            one_of(just([x] * 4), just([x] * 5), one_of(just([x] * 6), just([x] * 7))),
        ),
    )
)

for i in range(8):
    exec(
        f"""test_one_of_flattens_flatmap_branches_{i} = define_test(
        one_of_nested_strategy_with_flatmap, lambda x: len(x) == {i}
    )"""
    )


xor_nested_strategy_with_flatmap = just(None).flatmap(
    lambda x: (
        just([x] * 0)
        | just([x] * 1)
        | (
            just([x] * 2)
            | just([x] * 3)
            | (just([x] * 4) | just([x] * 5) | (just([x] * 6) | just([x] * 7)))
        )
    )
)

for i in range(8):
    exec(
        f"""test_xor_flattens_flatmap_branches_{i} = define_test(
        xor_nested_strategy_with_flatmap, lambda x: len(x) == {i}
    )"""
    )


# This strategy tests interactions with `filter()`.  It generates the even
# integers {0, 2, 4, 6} in equal measures.
one_of_nested_strategy_with_filter = one_of(
    just(0),
    just(1),
    one_of(just(2), just(3), one_of(just(4), just(5), one_of(just(6), just(7)))),
).filter(lambda x: x % 2 == 0)

for i in range(4):
    exec(
        f"""test_one_of_flattens_filter_branches_{i} = define_test(
        one_of_nested_strategy_with_filter, lambda x: x == 2 * {i}
    )"""
    )


test_long_duplicates_strings = define_test(
    tuples(text(), text()), lambda s: len(s[0]) >= 5 and s[0] == s[1]
)

test_can_produce_nasty_strings = define_test(
    text(), lambda s: s in {"NaN", "Inf", "undefined"}, p=0.01
)
