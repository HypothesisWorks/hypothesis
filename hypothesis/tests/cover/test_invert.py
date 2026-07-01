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
import datetime as dt
import math
import zoneinfo

import pytest

from hypothesis import given, settings, strategies as st
from hypothesis.control import BuildContext
from hypothesis.errors import CannotInvert
from hypothesis.internal.conjecture.data import ConjectureData
from hypothesis.internal.conjecture.junkdrawer import deep_equal

pytestmark = pytest.mark.skipif(
    settings().backend == "crosshair", reason="cannot _invert symbolic values"
)


def assert_roundtrip(strategy, value):
    choices = strategy._invert(value)
    data = ConjectureData.for_choices(choices)
    with BuildContext(data, is_final=False, wrapped_test=lambda: None):
        replayed = data.draw(strategy)

    assert data.misaligned_at is None
    assert deep_equal(data.choices, choices)
    assert deep_equal(replayed, value)


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
def test_just(data):
    value = data.draw(st.integers())
    check_roundtrip_many(st.just(value), data)


@given(st.data())
def test_none(data):
    check_roundtrip_many(st.none(), data)


@given(st.data())
def test_sampled_from(data):
    elements = data.draw(st.lists(st.integers(), min_size=1))
    check_roundtrip_many(st.sampled_from(elements), data)


@given(st.data())
def test_tuples(data):
    n = data.draw(st.integers(0, 5))
    check_roundtrip_many(st.tuples(*[st.integers()] * n), data)


@given(st.data())
def test_one_of(data):
    n = data.draw(st.integers(1, 5))
    check_roundtrip_many(st.one_of(*[st.integers()] * n), data)


@given(st.data())
def test_lists(data):
    min_size = data.draw(st.integers(0, 5))
    max_size = data.draw(st.integers(min_size, min_size + 10))
    strategy = st.lists(st.integers(), min_size=min_size, max_size=max_size)
    check_roundtrip_many(strategy, data)


@given(st.data())
def test_text(data):
    alphabet = data.draw(st.none() | st.text(min_size=1))
    min_size = data.draw(st.integers(0, 5))
    max_size = data.draw(st.integers(min_size, min_size + 10))
    kwargs = {"min_size": min_size, "max_size": max_size}
    if alphabet is not None:
        kwargs["alphabet"] = alphabet
    check_roundtrip_many(st.text(**kwargs), data)


@given(st.data())
def test_characters(data):
    check_roundtrip_many(st.characters(), data)


@given(st.data())
def test_floats_nan_via_filter(data):
    # st.floats(allow_nan=True).filter(math.isnan) is rewritten to NanStrategy.
    check_roundtrip_many(st.floats(allow_nan=True).filter(math.isnan), data)


@given(st.data())
def test_permutations(data):
    values = data.draw(st.lists(st.integers(), unique=True))
    check_roundtrip_many(st.permutations(values), data)


@given(st.data())
def test_dates(data):
    min_value = data.draw(st.dates())
    max_value = data.draw(st.dates(min_value=min_value))
    if min_value == max_value:
        max_value = max_value + dt.timedelta(days=1)
    check_roundtrip_many(st.dates(min_value=min_value, max_value=max_value), data)


@given(st.data())
def test_times(data):
    min_value = data.draw(st.times())
    max_value = data.draw(st.times(min_value=min_value))
    check_roundtrip_many(st.times(min_value=min_value, max_value=max_value), data)


@given(st.data())
def test_datetimes(data):
    min_value = data.draw(st.datetimes())
    max_value = data.draw(st.datetimes(min_value=min_value))
    check_roundtrip_many(st.datetimes(min_value=min_value, max_value=max_value), data)


@given(st.data())
def test_timedeltas(data):
    min_value = data.draw(st.timedeltas())
    max_value = data.draw(st.timedeltas(min_value=min_value))
    check_roundtrip_many(st.timedeltas(min_value=min_value, max_value=max_value), data)


@given(st.data())
def test_filter(data):
    # Bound threshold to the lower half of the range so at least half of all
    # values pass the filter (otherwise filter_too_much fires).
    lo = data.draw(st.integers(-100, 100))
    hi = data.draw(st.integers(lo, lo + 100))
    threshold = data.draw(st.integers(lo, lo + (hi - lo) // 2))
    check_roundtrip_many(st.integers(lo, hi).filter(lambda x: x >= threshold), data)


@dataclasses.dataclass
class _Pair:
    x: object
    y: object


@pytest.mark.parametrize("target", [list, dict, set, tuple, frozenset, int, str, bytes])
@given(data=st.data())
def test_builds_zero_arg(data, target):
    check_roundtrip_many(st.builds(target), data)


@given(st.data())
def test_builds_dataclass(data):
    # For each field, randomly choose positional or kwarg. Once we've gone
    # kwarg we can't go back to positional, so seen_kwarg latches.
    args = []
    kwargs = {}
    seen_kwarg = False
    for field in dataclasses.fields(_Pair):
        if seen_kwarg or data.draw(st.booleans()):
            kwargs[field.name] = st.integers()
            seen_kwarg = True
        else:
            args.append(st.integers())
    check_roundtrip_many(st.builds(_Pair, *args, **kwargs), data)


@given(st.data())
def test_deferred(data):
    check_roundtrip_many(st.deferred(lambda: st.integers()), data)


@given(st.data())
def test_recursive(data):
    check_roundtrip_many(
        st.recursive(st.integers(), lambda c: st.lists(c, max_size=2)), data
    )


@pytest.mark.parametrize(
    "strategy,value",
    [
        (st.floats(allow_nan=True), float("nan")),
        (st.integers().filter(lambda x: x % 2 == 0), 4),
        (st.sampled_from([1, 2, 3, 4]).filter(lambda x: x > 2), 3),
    ],
)
def test_roundtrip_explicit(strategy, value):
    assert_roundtrip(strategy, value)


@pytest.mark.parametrize(
    "strategy,value",
    [
        (st.integers(), True),
        (st.integers(), 1.0),
        (st.integers(), "5"),
        (st.floats(), 1),
        (st.floats(allow_subnormal=False), 5e-324),
        (st.booleans(), 0),
        (st.binary(), "abc"),
        (st.integers(0, 10), -1),
        (st.integers(0, 10), 11),
        (st.floats(min_value=0.0, max_value=1.0), 2.0),
        (st.floats(allow_nan=False), float("nan")),
        (st.binary(min_size=3, max_size=3), b"ab"),
        (st.lists(st.integers()), "not a list"),
        (st.lists(st.integers(), min_size=3), [1, 2]),
        (st.lists(st.integers(), max_size=2), [1, 2, 3]),
        (st.lists(st.integers(), unique=True), [1, 2, 3]),
        (st.lists(st.integers(), unique=True), object()),
        (st.tuples(st.integers(), st.booleans()), (5,)),
        (st.tuples(st.integers(), st.booleans()), (5, True, "extra")),
        (st.text(), 123),
        (st.text(max_size=2), "abc"),
        (st.text(alphabet="abc"), "xyz"),
        (st.characters(), "ab"),
        (st.characters(min_codepoint=ord("a"), max_codepoint=ord("z")), "A"),
        (st.floats(allow_nan=True).filter(math.isnan), 1.0),
        (st.text(st.text(min_size=1, max_size=1)), "a"),
        (st.dates(), "not a date"),
        (
            st.dates(min_value=dt.date(2020, 1, 1), max_value=dt.date(2021, 1, 1)),
            dt.date(2025, 1, 1),
        ),
        (st.times(), "not a time"),
        (st.times(min_value=dt.time(12, 0)), dt.time(6, 0)),
        (st.datetimes(), "not a datetime"),
        (
            st.datetimes(max_value=dt.datetime(2020, 1, 1)),
            dt.datetime(2025, 1, 1),
        ),
        # 2024-03-10 02:30 New York is in the imaginary gap
        (
            st.datetimes(
                allow_imaginary=False,
                timezones=st.just(zoneinfo.ZoneInfo("America/New_York")),
            ),
            dt.datetime(
                2024, 3, 10, 2, 30, tzinfo=zoneinfo.ZoneInfo("America/New_York")
            ),
        ),
        (st.timedeltas(), "not a timedelta"),
        (st.timedeltas(max_value=dt.timedelta(days=1)), dt.timedelta(days=10)),
        (st.just(42), 41),
        (st.sampled_from([1, 2, 3]), 99),
        (st.nothing(), 0),
        (st.integers().filter(lambda x: x > 0), -5),
        (st.integers().filter(lambda x: x % 2 == 0), 3),
        (st.one_of(st.integers(), st.booleans()), "string"),
        (st.permutations([1, 2, 3]), [4, 1, 2]),
        (st.permutations([1, 2, 3]), [1, 2, 4]),
        (st.permutations([1, 2, 3]), [1, 2]),
        (st.fixed_dictionaries({"a": st.integers()}), object()),
        (st.builds(_Pair, x=st.integers(), y=st.integers()), "not a Pair"),
        (st.integers().map(str), object()),
        (st.lists(st.integers()).map(set), object()),
        (st.sets(st.integers()), object()),
        (st.frozensets(st.integers()), object()),
        (st.dictionaries(st.text(), st.integers()), object()),
        (
            st.integers().flatmap(
                lambda n: st.lists(st.integers(), min_size=n, max_size=n)
            ),
            object(),
        ),
        (st.builds(lambda x, y: x + y, st.integers(), st.integers()), object()),
        (st.data(), object()),
        (st.runner(), object()),
        (st.randoms(), object()),
        (st.random_module(), object()),
        (st.from_regex(r"abc"), object()),
        (st.functions(), object()),
    ],
)
def test_uninvertible_raises(strategy, value):
    with pytest.raises(CannotInvert):
        strategy._invert(value)


@pytest.mark.parametrize(
    "strategy,value,expected",
    [
        (st.lists(st.integers()), [], (False,)),
        (st.lists(st.integers(), min_size=3, max_size=3), [1, 2, 3], (1, 2, 3)),
        (st.just(42), 42, ()),
        (st.sampled_from([7, 7, 7]), 7, (0,)),
        (st.one_of(st.just(5), st.just(5)), 5, (0,)),
        (st.one_of(st.integers(), st.text()), "hello", (1, "hello")),
        (st.lists(st.integers()), [1, 2], (True, 1, True, 2, False)),
        (st.lists(st.integers(), min_size=1, max_size=5), [42], (True, 42, False)),
        (st.tuples(st.integers(), st.booleans()), (5, True), (5, True)),
        (st.tuples(), (), ()),
        (
            st.one_of(st.integers(), st.lists(st.integers(), max_size=3)),
            [1, 2],
            (1, True, 1, True, 2, False),
        ),
        (
            st.lists(st.lists(st.integers(), max_size=2), max_size=2),
            [[1], []],
            (True, True, 1, False, True, False, False),
        ),
        # Fisher-Yates inversion: each draw is the swap target index.
        (st.permutations([1, 2, 3]), [1, 2, 3], (0, 1)),
        (st.permutations([1, 2, 3]), [3, 1, 2], (2, 2)),
        (
            st.dates(min_value=dt.date(2020, 1, 1), max_value=dt.date(2025, 12, 31)),
            dt.date(2022, 5, 15),
            (2022, 5, 15),
        ),
        (st.integers().filter(lambda x: x > 0), 5, (5,)),
    ],
)
def test_produces_expected_choice_sequence(strategy, value, expected):
    assert strategy._invert(value) == expected
