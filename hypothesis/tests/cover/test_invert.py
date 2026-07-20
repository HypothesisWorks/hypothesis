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
from collections import OrderedDict

import pytest

from hypothesis import given, settings, strategies as st
from hypothesis.control import BuildContext
from hypothesis.errors import CannotInvert
from hypothesis.internal.conjecture.choice import ValueHole
from hypothesis.internal.conjecture.data import ConjectureData
from hypothesis.internal.conjecture.junkdrawer import deep_equal
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
    assert deep_equal(data.choices, tuple(choices))
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
    check_roundtrip_many(st.integers() | st.text() | st.booleans(), data)


@given(st.data())
def test_lists(data):
    min_size = data.draw(st.integers(0, 5))
    max_size = data.draw(st.integers(min_size, min_size + 10))
    strategy = st.lists(st.integers(), min_size=min_size, max_size=max_size)
    check_roundtrip_many(strategy, data)


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
        # dates() with min_value == max_value collapses to just()
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
def test_unique_lists(data):
    check_roundtrip_many(st.lists(st.integers(), unique=True), data)


@given(st.data())
def test_unique_sampled_lists(data):
    elements = data.draw(st.lists(st.integers(), min_size=1, unique=True))
    check_roundtrip_many(st.lists(st.sampled_from(elements), unique=True), data)


@given(st.data())
def test_unique_lists_of_tuples(data):
    # rearranged into element_strategy=integers plus tuple_suffixes
    strategy = st.lists(st.tuples(st.integers(), st.text()), unique_by=lambda t: t[0])
    check_roundtrip_many(strategy, data)


@given(st.data())
def test_dictionaries(data):
    min_size = data.draw(st.integers(0, 3))
    max_size = data.draw(st.none() | st.integers(min_size + 1, min_size + 5))
    strategy = st.dictionaries(
        st.text(), st.integers(), min_size=min_size, max_size=max_size
    )
    check_roundtrip_many(strategy, data)


@given(st.data())
def test_dictionaries_with_dict_class(data):
    strategy = st.dictionaries(st.text(), st.integers(), dict_class=OrderedDict)
    check_roundtrip_many(strategy, data)


@given(st.data())
def test_dictionaries_sampled_keys(data):
    # small integer keys draw from a fixed pool via UniqueSampledListStrategy
    check_roundtrip_many(st.dictionaries(st.integers(0, 5), st.booleans()), data)


@given(st.data())
def test_fixed_dictionaries(data):
    check_roundtrip_many(
        st.fixed_dictionaries({"a": st.integers(), "b": st.booleans()}), data
    )


@given(st.data())
def test_fixed_dictionaries_with_optional(data):
    strategy = st.fixed_dictionaries(
        {"a": st.integers()}, optional={"b": st.integers(), "c": st.text()}
    )
    check_roundtrip_many(strategy, data)


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
        (st.floats(allow_nan=True), math.nan),
        (st.integers().filter(lambda x: x % 2 == 0), 4),
        (st.sampled_from([1, 2, 3, 4]).filter(lambda x: x > 2), 3),
        (st.recursive(st.integers(), st.lists), [[1], [2, [3]]]),
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
        (st.lists(st.integers()), "not a list"),
        (st.lists(st.integers(), min_size=3), [1, 2]),
        (st.lists(st.integers(), max_size=2), [1, 2, 3]),
        (st.lists(st.integers(), unique=True), [1, 1]),
        (st.lists(st.sampled_from([1, 2, 3]), unique=True), [1, 4]),
        # duplicate keys, unrepresentable in a dict but not in the list form
        (
            st.lists(st.tuples(st.integers(), st.text()), unique_by=lambda t: t[0]),
            [(1, "x"), (1, "y")],
        ),
        (st.dictionaries(st.text(), st.integers()), {1: 2}),
        (st.dictionaries(st.text(), st.integers()), [("a", 1)]),
        (st.dictionaries(st.text(), st.integers(), max_size=1), {"a": 1, "b": 2}),
        (st.fixed_dictionaries({"a": st.integers()}), {"a": 1, "z": 2}),
        (st.fixed_dictionaries({"a": st.integers()}), {}),
        (st.fixed_dictionaries({"a": st.integers()}), {"a": "not an int"}),
        (
            st.fixed_dictionaries({"a": st.integers()}, optional={"b": st.nothing()}),
            {"a": 1, "b": 2},
        ),
        (st.tuples(st.integers(), st.booleans()), (5,)),
        (st.tuples(st.integers(), st.booleans()), (5, True, "extra")),
        (st.floats(allow_nan=True).filter(math.isnan), 1.0),
        (st.dates(), "not a date"),
        (
            st.dates(min_value=dt.date(2020, 1, 1), max_value=dt.date(2021, 1, 1)),
            dt.date(2025, 1, 1),
        ),
        (st.times(), "not a time"),
        (st.times(min_value=dt.time(12, 0)), dt.time(6, 0)),
        (st.datetimes(), "not a datetime"),
        (st.datetimes(max_value=dt.datetime(2020, 1, 1)), dt.datetime(2025, 1, 1)),
        # 2024-03-10 02:30 New York is in the imaginary DST gap
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
        (st.builds(_Pair, x=st.integers(), y=st.integers()), "not a Pair"),
    ],
)
def test_out_of_image_raises(strategy, value):
    with pytest.raises(CannotInvert):
        strategy._invert(value)


@pytest.mark.parametrize(
    "strategy,value",
    [
        (st.integers().map(str), "1"),
        # a mapped element strategy is not rewritten to OneCharStringStrategy
        # (unlike e.g. sampled_from of characters, which is)
        (st.text(st.characters().map(str.upper), max_size=5), "A"),
        (st.sets(st.integers()), {1}),
        (st.frozensets(st.integers()), frozenset()),
        (st.builds(lambda x, y: x + y, st.integers(), st.integers()), 3),
        (st.shared(st.integers()), 0),
        (
            st.integers().flatmap(
                lambda n: st.lists(st.integers(), min_size=n, max_size=n)
            ),
            [1],
        ),
        (st.data(), None),
        (st.runner(), None),
        (st.randoms(), None),
        (st.random_module(), None),
        (st.from_regex(r"abc"), "abc"),
        (st.functions(), None),
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
        # ties in encoding length break towards the lower branch index
        (st.one_of(st.just(5), st.just(5)), 5, (0,)),
        # ...but a shorter encoding beats a lower index
        (
            st.one_of(st.lists(st.booleans(), min_size=1), st.just([True])),
            [True],
            (1,),
        ),
        # ...except that a two-choice candidate is accepted immediately,
        # without scanning later branches for a one-choice just()-like one
        (st.one_of(st.lists(st.booleans()), st.just([])), [], (0, False)),
        (st.just(42), 42, ()),
        (st.sampled_from([7, 7, 7]), 7, (0,)),
        (st.lists(st.integers()), [], (False,)),
        (st.lists(st.integers()), [1, 2], (True, 1, True, 2, False)),
        (st.lists(st.integers(), min_size=3, max_size=3), [1, 2, 3], (1, 2, 3)),
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
        (st.timedeltas(), dt.timedelta(days=2, seconds=3), (2, 3, 0)),
        (st.dictionaries(st.text(), st.integers()), {}, (False,)),
        (st.dictionaries(st.text(), st.integers()), {"a": 1}, (True, "a", 1, False)),
        # required value, then presence-selection of the optional key and its
        # value, then an identity shuffle of the two pairs
        (
            st.fixed_dictionaries({"a": st.integers()}, optional={"b": st.booleans()}),
            {"a": 5, "b": True},
            (5, True, 0, True, False, 0),
        ),
        (
            st.fixed_dictionaries({"a": st.integers()}, optional={"b": st.booleans()}),
            {"a": 5},
            (5, False),
        ),
        (st.integers().filter(lambda x: x > 0), 5, (5,)),
    ],
)
def test_produces_expected_choice_sequence(strategy, value, expected):
    assert strategy._invert(value) == expected


def test_datetime_produces_expected_choice_sequence():
    # the timezone is drawn first (contributing no choices for just(None)),
    # then year down to microsecond, then fold
    value = dt.datetime(2021, 6, 5, 4, 3, 2, 1, fold=1)
    assert st.datetimes()._invert(value) == (2021, 6, 5, 4, 3, 2, 1, 1)
    # times() draws fold before the timezone
    assert st.times()._invert(dt.time(1, 2, 3, 4)) == (1, 2, 3, 4, 0)


def test_nan_roundtrips():
    assert_roundtrip(st.floats(), math.nan)
    # a nonstandard nan bitpattern
    assert_roundtrip(st.floats(), -math.nan)


def test_failed_inversion_notes_the_path_to_the_failure():
    with pytest.raises(CannotInvert) as excinfo:
        st.lists(st.lists(st.integers()))._invert([[1], ["a"]])
    assert any("at index 0 of ['a']" in note for note in excinfo.value.__notes__)
    assert any("at index 1 of [[1], ['a']]" in note for note in excinfo.value.__notes__)


def test_self_referential_strategies_do_not_recurse_forever():
    # Directly self-referential unions collapse the self-branch when
    # flattening, but a wrapper (like .filter) hides the cycle from
    # flattening; the reentrancy guard in OneOfStrategy._invert catches it.
    x = st.deferred(lambda: st.integers() | x.filter(lambda v: True))
    assert x._invert(5) == (0, 5)

    y = st.deferred(lambda: y.filter(lambda v: True) | st.integers())
    assert y._invert(5)[-1] == 5
    assert_roundtrip(y, 5)


def test_lazy_strategy_delegates_invert():
    s = st.integers(123, 456)
    assert isinstance(s, LazyStrategy)
    assert s._invert(200) == (200,)


def hole(value):
    return ValueHole(value, record=True)


@pytest.mark.parametrize(
    "strategy,value,expected",
    [
        # a fully-invertible value produces the same choices as _invert
        (st.tuples(st.integers(), st.booleans()), (5, True), (5, True)),
        # subtrees which cannot invert become holes; the rest stay concrete
        (
            st.tuples(st.integers(), st.integers().map(str), st.booleans()),
            (1, "2", True),
            (1, hole("2"), True),
        ),
        (
            st.lists(st.integers().map(lambda x: x * 2)),
            [2, 4],
            (True, hole(2), True, hole(4), False),
        ),
        (
            st.lists(st.tuples(st.integers(), st.integers().map(str))),
            [(1, "2")],
            (True, 1, hole("2"), False),
        ),
        # a strategy with no structural override becomes a single hole
        (st.integers().map(str), "5", (hole("5"),)),
        # a one_of only re-encodes into a branch which inverts completely;
        # otherwise it becomes a single hole covering the whole union, even
        # when a branch could have partially inverted the value
        (st.integers() | st.text().map(str.upper), 5, (0, 5)),
        (st.integers() | st.text().map(str.upper), "ABC", (hole("ABC"),)),
        (
            st.booleans() | st.lists(st.integers().map(str)),
            ["1"],
            (hole(["1"]),),
        ),
        # fixed_dictionaries: values in mapping order, then an identity
        # shuffle of the pairs
        (
            st.fixed_dictionaries({"a": st.integers(), "b": st.integers().map(str)}),
            {"a": 1, "b": "2"},
            (1, hole("2"), 0),
        ),
        (
            st.fixed_dictionaries({"a": st.integers()}),
            {"mismatched": 1},
            (hole({"mismatched": 1}),),
        ),
        (
            st.builds(_Pair, x=st.integers(), y=st.integers().map(str)),
            _Pair(1, "2"),
            (
                1,
                hole("2"),
            ),
        ),
        # filters pass through when the condition holds, and hole otherwise
        (
            st.lists(st.integers().map(str)).filter(len),
            ["1"],
            (True, hole("1"), False),
        ),
        (st.lists(st.integers().map(str)).filter(len), [], (hole([]),)),
        # shape mismatches also degrade to a single hole
        (st.tuples(st.integers()), "not a tuple", (hole("not a tuple"),)),
        (st.lists(st.integers(), max_size=1), [1, 2], (hole([1, 2]),)),
        (st.lists(st.integers(), unique=True), [1, 1], (hole([1, 1]),)),
    ],
)
def test_invert_with_holes_shapes(strategy, value, expected):
    assert strategy._invert_with_holes(value) == expected
