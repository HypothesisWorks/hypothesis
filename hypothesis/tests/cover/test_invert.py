# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import math

import pytest

from hypothesis import given, settings, strategies as st
from hypothesis.control import BuildContext
from hypothesis.errors import CannotInvert
from hypothesis.internal.conjecture.choice import choice_equal
from hypothesis.internal.conjecture.data import ConjectureData
from hypothesis.strategies._internal.lazy import LazyStrategy

pytestmark = pytest.mark.skipif(
    settings().backend == "crosshair", reason="cannot _invert symbolic values"
)


def assert_roundtrip(strategy, value):
    # note: for lazily-defined strategies this exercises LazyStrategy._invert
    choices = strategy._invert(value)
    data = ConjectureData.for_choices(choices)
    with BuildContext(data, wrapped_test=lambda: None):
        replayed = data.draw(strategy)

    assert data.misaligned_at is None
    assert len(data.choices) == len(choices)
    assert all(map(choice_equal, data.choices, choices))
    assert choice_equal(replayed, value)


def check_roundtrip_many(strategy, data):
    for _ in range(5):
        assert_roundtrip(strategy, data.draw(strategy))


@given(st.data())
def test_integers(data):
    min_value = data.draw(st.none() | st.integers())
    max_value = data.draw(st.none() | st.integers())
    if min_value is not None and max_value is not None and min_value > max_value:
        min_value, max_value = max_value, min_value
    check_roundtrip_many(st.integers(min_value, max_value), data)


@given(st.data())
def test_booleans(data):
    check_roundtrip_many(st.booleans(), data)


@given(st.data())
def test_floats(data):
    min_value = data.draw(st.none() | st.floats(allow_nan=False))
    max_value = data.draw(st.none() | st.floats(allow_nan=False))
    if min_value is not None and max_value is not None and min_value > max_value:
        min_value, max_value = max_value, min_value
    bounded = min_value is not None or max_value is not None
    allow_nan = False if bounded else data.draw(st.booleans())
    strategy = st.floats(min_value=min_value, max_value=max_value, allow_nan=allow_nan)
    check_roundtrip_many(strategy, data)


@given(st.data())
def test_binary(data):
    min_size = data.draw(st.integers(0, 20))
    max_size = data.draw(st.integers(min_size, min_size + 20))
    check_roundtrip_many(st.binary(min_size=min_size, max_size=max_size), data)


@given(st.data())
def test_text(data):
    alphabet = data.draw(st.none() | st.text(min_size=1))
    min_size = data.draw(st.integers(0, 5))
    # max_size=0 would collapse to just(""), which does not support inversion
    max_size = data.draw(st.integers(max(min_size, 1), min_size + 10))
    kwargs = {"min_size": min_size, "max_size": max_size}
    if alphabet is not None:
        kwargs["alphabet"] = alphabet
    check_roundtrip_many(st.text(**kwargs), data)


@given(st.data())
def test_characters(data):
    check_roundtrip_many(st.characters(), data)


@pytest.mark.parametrize(
    "strategy,value",
    [
        (st.integers(), True),
        (st.integers(), 1.0),
        (st.integers(), "5"),
        (st.integers(0, 10), -1),
        (st.integers(0, 10), 11),
        (st.floats(), 1),
        (st.floats(allow_subnormal=False), 5e-324),
        (st.floats(min_value=0.0, max_value=1.0), 2.0),
        (st.floats(allow_nan=False), math.nan),
        (st.one_of(st.integers(), st.text()), b"not an int or str"),
        (st.booleans(), 0),
        (st.binary(), "abc"),
        (st.binary(min_size=3, max_size=3), b"ab"),
        (st.text(), 123),
        (st.text(max_size=2), "abc"),
        (st.text(alphabet="abc"), "xyz"),
        (st.text(), "\ud800"),  # even unconstrained text() excludes surrogates
        (st.characters(), "ab"),
        (st.characters(min_codepoint=ord("a"), max_codepoint=ord("z")), "A"),
    ],
)
def test_out_of_image_raises(strategy, value):
    with pytest.raises(CannotInvert):
        strategy._invert(value)


@pytest.mark.parametrize(
    "strategy,value",
    [
        (st.just(42), 42),
        (st.sampled_from([1, 2, 3]), 1),
        (st.lists(st.integers()), [1]),
        (st.tuples(st.integers()), (1,)),
        # one_of delegates to its branches, none of which can invert this
        (st.one_of(st.lists(st.integers()), st.tuples(st.integers())), [1]),
        (st.integers().map(str), "1"),
        # an opaque predicate, to dodge filter-rewriting into IntegersStrategy
        (st.integers().filter(lambda x: (x**3 - x) % 7 == 0), 0),
        # a mapped element strategy is not rewritten to OneCharStringStrategy
        # (unlike e.g. sampled_from of characters, which is)
        (st.text(st.characters().map(str.upper), max_size=5), "A"),
    ],
)
def test_unimplemented_raises(strategy, value):
    with pytest.raises(CannotInvert):
        strategy._invert(value)


@pytest.mark.parametrize(
    "strategy,value,expected",
    [
        (st.integers(), 5, (5,)),
        (st.booleans(), False, (False,)),
        (st.floats(), math.inf, (math.inf,)),
        (st.text(), "hello", ("hello",)),
        (st.binary(), b"ab", (b"ab",)),
        (st.characters(), "a", ("a",)),
        (st.one_of(st.integers(), st.text()), 5, (0, 5)),
        (st.one_of(st.integers(), st.text()), "hi", (1, "hi")),
        # branches which cannot hold the value are skipped
        (st.one_of(st.booleans(), st.integers()), 7, (1, 7)),
        # equal-length candidates keep the earlier branch
        (st.one_of(st.integers(), st.integers(0, 10)), 5, (0, 5)),
    ],
)
def test_produces_expected_choice_sequence(strategy, value, expected):
    assert strategy._invert(value) == expected


def test_nan_roundtrips():
    assert_roundtrip(st.floats(), math.nan)
    # a nonstandard nan bitpattern
    assert_roundtrip(st.floats(), -math.nan)


@given(st.data())
def test_one_of(data):
    check_roundtrip_many(st.integers() | st.text() | st.booleans(), data)


def test_lazy_strategy_delegates_invert():
    s = st.integers(123, 456)
    assert isinstance(s, LazyStrategy)
    assert s._invert(200) == (200,)
