# coding=utf-8

# Copyright (C) 2013-2015 David R. MacIver (david@drmaciver.com)

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

from __future__ import division, print_function, absolute_import, \
    unicode_literals

import random
from collections import namedtuple

import pytest
import hypothesis.specifiers as specifiers
from hypothesis.types import RandomWithSeed
from hypothesis.errors import NoExamples
from hypothesis.internal.compat import hrange, text_type
from hypothesis.searchstrategy.numbers import BoundedIntStrategy, \
    RandomGeometricIntStrategy
from hypothesis.searchstrategy.strategies import BuildContext, \
    OneOfStrategy, strategy, one_of_strategies


def test_or_errors_when_given_non_strategy():
    bools = strategy((bool,))
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
    just_one_integer = strategy(specifiers.IntegerRange(1, 1))
    for _ in hrange(100):
        pv = just_one_integer.draw_parameter(random)
        x = just_one_integer.produce_template(BuildContext(random), pv)
        assert x == 1
    some_integers = strategy(specifiers.IntegerRange(1, 10))
    for _ in hrange(100):
        pv = some_integers.produce_parameter(random)
        x = some_integers.produce_template(BuildContext(random), pv)
        assert 1 <= x <= 10


def test_strategy_for_integer_range_can_produce_end_points():
    some_integers = strategy(specifiers.IntegerRange(1, 10))
    found = set()
    for _ in hrange(1000):  # pragma: no branch
        pv = some_integers.produce_parameter(random)
        x = some_integers.produce_template(BuildContext(random), pv)
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
    rnd = strategy(random.Random).example()
    seed = rnd.seed
    assert text_type(seed) in repr(rnd)


def test_random_only_produces_special_random():
    st = strategy(random.Random)
    assert isinstance(st.example(), RandomWithSeed)


def test_just_strategy_uses_repr():
    class WeirdRepr(object):

        def __repr__(self):
            return 'ABCDEFG'

    assert repr(
        strategy(specifiers.just(WeirdRepr()))
    ) == 'JustStrategy(value=%r)' % (WeirdRepr(),)


def test_can_map():
    s = strategy(int).map(pack=lambda t: 'foo')
    assert s.example() == 'foo'


def test_sample_from_empty_errors():
    with pytest.raises(ValueError):
        strategy(specifiers.sampled_from([]))


def test_example_raises_unsatisfiable_when_too_filtered():
    with pytest.raises(NoExamples):
        strategy(int).filter(lambda x: False).example()
