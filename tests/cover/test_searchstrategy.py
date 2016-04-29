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

from __future__ import division, print_function, absolute_import

import functools
from collections import namedtuple

import pytest

from hypothesis.types import RandomWithSeed
from hypothesis.errors import NoExamples
from hypothesis.strategies import just, tuples, randoms, booleans, integers
from hypothesis.internal.compat import text_type
from hypothesis.searchstrategy.strategies import one_of_strategies


def test_or_errors_when_given_non_strategy():
    bools = tuples(booleans())
    with pytest.raises(ValueError):
        bools | u'foo'


def test_joining_zero_strategies_fails():
    with pytest.raises(ValueError):
        one_of_strategies(())


SomeNamedTuple = namedtuple(u'SomeNamedTuple', (u'a', u'b'))


def last(xs):
    t = None
    for x in xs:
        t = x
    return t


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
            return u'ABCDEFG'

    assert repr(
        just(WeirdRepr())
    ) == u'just(%r)' % (WeirdRepr(),)


def test_can_map():
    s = integers().map(pack=lambda t: u'foo')
    assert s.example() == u'foo'


def test_example_raises_unsatisfiable_when_too_filtered():
    with pytest.raises(NoExamples):
        integers().filter(lambda x: False).example()


def nameless_const(x):
    def f(u, v):
        return u
    return functools.partial(f, x)


def test_can_map_nameless():
    f = nameless_const(2)
    assert repr(f) in repr(integers().map(f))


def test_can_flatmap_nameless():
    f = nameless_const(just(3))
    assert repr(f) in repr(integers().flatmap(f))
