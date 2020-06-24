# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Most of this work is copyright (C) 2013-2020 David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
# CONTRIBUTING.rst for a full list of people who may hold copyright, and
# consult the git log if you need to determine who owns an individual
# contribution.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.
#
# END HEADER

import functools
from collections import namedtuple

import pytest

from hypothesis.errors import InvalidArgument
from hypothesis.strategies import booleans, integers, just, tuples
from hypothesis.strategies._internal.strategies import one_of_strategies
from tests.common.debug import assert_no_examples


def test_or_errors_when_given_non_strategy():
    bools = tuples(booleans())
    with pytest.raises(ValueError):
        bools | "foo"


def test_joining_zero_strategies_fails():
    with pytest.raises(ValueError):
        one_of_strategies(())


SomeNamedTuple = namedtuple("SomeNamedTuple", ("a", "b"))


def last(xs):
    t = None
    for x in xs:
        t = x
    return t


def test_just_strategy_uses_repr():
    class WeirdRepr:
        def __repr__(self):
            return "ABCDEFG"

    assert repr(just(WeirdRepr())) == "just(%r)" % (WeirdRepr(),)


def test_can_map():
    s = integers().map(pack=lambda t: "foo")
    assert s.example() == "foo"


def test_example_raises_unsatisfiable_when_too_filtered():
    assert_no_examples(integers().filter(lambda x: False))


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


def test_flatmap_with_invalid_expand():
    with pytest.raises(InvalidArgument):
        just(100).flatmap(lambda n: "a").example()
