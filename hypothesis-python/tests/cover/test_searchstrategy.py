# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import dataclasses
import functools
import random
import sys
from collections import defaultdict, namedtuple

import attr
import pytest

from hypothesis import given, strategies as st
from hypothesis.errors import InvalidArgument, Unsatisfiable
from hypothesis.internal.conjecture.data import ConjectureData
from hypothesis.internal.reflection import get_pretty_function_description
from hypothesis.strategies._internal.utils import to_jsonable

from tests.common.debug import assert_simple_property, check_can_generate_examples
from tests.common.utils import checks_deprecated_behaviour


def test_or_errors_when_given_non_strategy():
    bools = st.tuples(st.booleans())
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

    assert repr(st.just(WeirdRepr())) == f"just({WeirdRepr()!r})"


def test_just_strategy_does_not_draw():
    data = ConjectureData.for_choices([])
    s = st.just("hello")
    assert s.do_draw(data) == "hello"


def test_none_strategy_does_not_draw():
    data = ConjectureData.for_choices([])
    s = st.none()
    assert s.do_draw(data) is None


def test_can_map():
    s = st.integers().map(pack=lambda t: "foo")
    assert_simple_property(s, lambda v: v == "foo")


def test_example_raises_unsatisfiable_when_too_filtered():
    with pytest.raises(Unsatisfiable):
        check_can_generate_examples(st.integers().filter(lambda x: False))


def nameless_const(x):
    def f(u, v):
        return u

    return functools.partial(f, x)


def test_can_map_nameless():
    f = nameless_const(2)
    assert get_pretty_function_description(f) in repr(st.integers().map(f))


def test_can_flatmap_nameless():
    f = nameless_const(st.just(3))
    assert get_pretty_function_description(f) in repr(st.integers().flatmap(f))


def test_flatmap_with_invalid_expand():
    with pytest.raises(InvalidArgument):
        check_can_generate_examples(st.just(100).flatmap(lambda n: "a"))


_bad_random_strategy = st.lists(st.integers(), min_size=1).map(random.choice)


@checks_deprecated_behaviour
def test_use_of_global_random_is_deprecated_in_given():
    check_can_generate_examples(_bad_random_strategy)


@checks_deprecated_behaviour
def test_use_of_global_random_is_deprecated_in_interactive_draws():
    @given(st.data())
    def inner(d):
        d.draw(_bad_random_strategy)

    inner()


def test_jsonable():
    assert to_jsonable(object(), avoid_realization=True) == "<symbolic>"
    assert isinstance(to_jsonable(object(), avoid_realization=False), str)


@dataclasses.dataclass()
class HasDefaultDict:
    x: defaultdict


@attr.s
class AttrsClass:
    n = attr.ib()


def test_jsonable_defaultdict():
    obj = HasDefaultDict(defaultdict(list))
    obj.x["a"] = [42]
    assert to_jsonable(obj, avoid_realization=False) == {"x": {"a": [42]}}


def test_jsonable_attrs():
    obj = AttrsClass(n=10)
    assert to_jsonable(obj, avoid_realization=False) == {"n": 10}


def test_jsonable_namedtuple():
    Obj = namedtuple("Obj", ("x"))
    obj = Obj(10)
    assert to_jsonable(obj, avoid_realization=False) == {"x": 10}


def test_jsonable_small_ints_are_ints():
    n = 2**62
    for avoid in (True, False):
        assert isinstance(to_jsonable(n, avoid_realization=avoid), int)
        assert to_jsonable(n, avoid_realization=avoid) == n


def test_jsonable_large_ints_are_floats():
    n = 2**63
    assert isinstance(to_jsonable(n, avoid_realization=False), float)
    assert to_jsonable(n, avoid_realization=False) == float(n)
    assert to_jsonable(n, avoid_realization=True) == "<symbolic>"


def test_jsonable_very_large_ints():
    # previously caused OverflowError when casting to float.
    n = 2**1024
    assert to_jsonable(n, avoid_realization=False) == sys.float_info.max
    assert to_jsonable(n, avoid_realization=True) == "<symbolic>"


@dataclasses.dataclass()
class HasCustomJsonFormat:
    x: str

    def to_json(self):
        return "surprise!"


def test_jsonable_override():
    obj = HasCustomJsonFormat("expected")
    assert to_jsonable(obj, avoid_realization=False) == "surprise!"
    assert to_jsonable(obj, avoid_realization=True) == "<symbolic>"


def test_deferred_strategy_draw():
    strategy = st.deferred(lambda: st.integers())
    assert strategy.do_draw(ConjectureData.for_choices([0])) == 0
