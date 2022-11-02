# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import functools
from collections import namedtuple

import pytest

from tests.common.debug import assert_no_examples

from hypothesis.errors import InvalidArgument
from hypothesis.internal.conjecture.data import ConjectureData
from hypothesis.strategies import booleans, integers, just, none, tuples


def test_or_errors_when_given_non_strategy():
    bools = tuples(booleans())
    with pytest.raises(ValueError):
        bools | "foo"


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

    assert repr(just(WeirdRepr())) == f"just({WeirdRepr()!r})"


def test_just_strategy_does_not_draw():
    data = ConjectureData.for_buffer(b"")
    s = just("hello")
    assert s.do_draw(data) == "hello"


def test_none_strategy_does_not_draw():
    data = ConjectureData.for_buffer(b"")
    s = none()
    assert s.do_draw(data) is None


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
