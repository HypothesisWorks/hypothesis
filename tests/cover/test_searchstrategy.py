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

from __future__ import division, print_function, absolute_import, \
    unicode_literals

import math
import random
import functools
from collections import namedtuple

import pytest
import hypothesis.specifiers as specifiers
from hypothesis.types import RandomWithSeed
from hypothesis.errors import NoExamples, InvalidArgument
from hypothesis.strategies import just, tuples, randoms, booleans, \
    integers, frozensets, sampled_from
from hypothesis.internal.compat import hrange, text_type
from hypothesis.searchstrategy.numbers import BoundedIntStrategy, \
    RandomGeometricIntStrategy
from hypothesis.searchstrategy.strategies import OneOfStrategy, \
    one_of_strategies


def test_or_errors_when_given_non_strategy():
    bools = tuples(booleans())
    with pytest.raises(ValueError):
        bools | 'foo'


def test_joining_zero_strategies_fails():
    with pytest.raises(ValueError):
        one_of_strategies(())


def test_directly_joining_one_strategy_also_fails():
    with pytest.raises(ValueError):
        OneOfStrategy([RandomGeometricIntStrategy()])

SomeNamedTuple = namedtuple('SomeNamedTuple', ('a', 'b'))


def test_strategy_for_integer_range_produces_only_integers_in_that_range():
    just_one_integer = integers(1, 1)
    for _ in hrange(100):
        pv = just_one_integer.draw_parameter(random)
        t = just_one_integer.draw_template(random, pv)
        x = just_one_integer.reify(t)
        assert x == 1
    some_integers = integers(1, 10)
    for _ in hrange(100):
        pv = some_integers.draw_parameter(random)
        x = some_integers.draw_template(random, pv)
        assert 1 <= x <= 10


def test_strategy_for_integer_range_can_produce_end_points():
    some_integers = integers(1, 10)
    found = set()
    for _ in hrange(1000):  # pragma: no branch
        pv = some_integers.draw_parameter(random)
        x = some_integers.draw_template(random, pv)
        found.add(x)
        if 1 in found and 10 in found:
            break
    else:
        assert False  # pragma: no cover
    assert 1 in found
    assert 10 in found


def last(xs):
    t = None
    for x in xs:
        t = x
    return t


def test_rejects_invalid_ranges():
    with pytest.raises(ValueError):
        BoundedIntStrategy(10, 9)


def test_random_repr_has_seed():
    rnd = randoms().example()
    seed = rnd.seed
    assert text_type(seed) in repr(rnd)


def test_random_only_produces_special_random():
    st = randoms()
    assert isinstance(st.example(), RandomWithSeed)


def test_just_strategy_uses_repr():
    class WeirdRepr(object):

        def __repr__(self):
            return 'ABCDEFG'

    assert repr(
        just(WeirdRepr())
    ) == 'just(%r)' % (WeirdRepr(),)


def test_can_map():
    s = integers().map(pack=lambda t: 'foo')
    assert s.example() == 'foo'


def test_sample_from_empty_errors():
    with pytest.raises(InvalidArgument):
        sampled_from([])


def test_example_raises_unsatisfiable_when_too_filtered():
    with pytest.raises(NoExamples):
        integers().filter(lambda x: False).example()


def test_large_enough_integer_ranges_are_infinite():
    assert math.isinf(
        integers(1, 2 ** 64).template_upper_bound)


def test_tuple_strategy_too_large_to_fit():
    x = frozensets(integers(0, 5))
    assert not math.isinf(x.template_upper_bound)
    x = tuples(x, x)
    assert not math.isinf(x.template_upper_bound)
    assert math.isinf(tuples(x, x).template_upper_bound)
    assert math.isinf(
        tuples(integers(), x).template_upper_bound)


def test_one_of_strategy_goes_infinite():
    x = integers(0, 2 ** 32 - 2)
    assert not math.isinf(x.template_upper_bound)
    for _ in hrange(10):
        x |= x
    assert math.isinf(x.template_upper_bound)


def nameless_const(x):
    def f(u, v):
        return u
    return functools.partial(f, x)


def test_can_map_nameless():
    assert '0x' not in repr(integers().map(nameless_const(2)))


def test_can_flatmap_nameless():
    assert '0x' not in repr(integers().flatmap(
        nameless_const(specifiers.just(3))))
