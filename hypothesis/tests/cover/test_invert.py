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
from hypothesis.internal.compat import PYPY
from hypothesis.internal.conjecture.choice import (
    HOLE_LIMIT,
    Impossible,
    InvertAborted,
    ValueHole,
    _hole_budget,
    choice_equal,
)
from hypothesis.internal.conjecture.data import ConjectureData
from hypothesis.internal.conjecture.junkdrawer import equal_values
from hypothesis.internal.invertstring import string_template
from hypothesis.strategies._internal.lazy import LazyStrategy, unwrap_strategies
from hypothesis.strategies._internal.strategies import one_of

pytestmark = pytest.mark.skipif(
    settings().backend == "crosshair", reason="cannot _invert symbolic values"
)


def assert_roundtrip(strategy, value):
    # note: for lazily-defined strategies this exercises LazyStrategy._invert
    choices = strategy._invert(value)
    assert isinstance(choices, tuple)
    assert not any(isinstance(c, ValueHole) for c in choices)
    data = ConjectureData.for_choices(choices)
    with BuildContext(data, wrapped_test=lambda: None):
        replayed = data.draw(strategy)

    assert data.misaligned_at is None
    assert len(data.choices) == len(choices)
    assert all(map(choice_equal, data.choices, choices))
    assert equal_values(replayed, value)


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
    kwargs = {}
    min_size = data.draw(st.none() | st.integers(0, 5))
    if min_size is not None:
        kwargs["min_size"] = min_size
    lo = min_size or 0
    max_size = data.draw(st.none() | st.integers(lo, lo + 10))
    if max_size is not None:
        kwargs["max_size"] = max_size
    check_roundtrip_many(st.lists(st.integers(), **kwargs), data)


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


_NY = zoneinfo.ZoneInfo("America/New_York")
_UTC = zoneinfo.ZoneInfo("UTC")


class _RaisingTzinfo(dt.tzinfo):
    def utcoffset(self, value):
        raise RuntimeError("broken tzinfo")


@given(st.data())
def test_aware_datetimes(data):
    tz = data.draw(st.sampled_from([_UTC, _NY]))
    strategy = st.datetimes(
        dt.datetime(2020, 1, 1, tzinfo=_NY),
        dt.datetime(2021, 1, 1, tzinfo=_NY),
        timezones=st.just(tz),
    )
    check_roundtrip_many(strategy, data)


@given(st.data())
def test_aware_datetimes_with_sampled_timezones(data):
    strategy = st.datetimes(
        dt.datetime(2020, 1, 1, tzinfo=_UTC),
        dt.datetime(2021, 1, 1, tzinfo=_UTC),
        timezones=st.sampled_from([_UTC, _NY]),
    )
    check_roundtrip_many(strategy, data)


@given(st.data())
def test_aware_datetimes_in_utc_recursion_frame(data):
    # Bounds inside the same DST fold are in inverted wall-clock order, so
    # generation - and therefore inversion - goes through the UTC frame.
    strategy = st.datetimes(
        dt.datetime(2020, 11, 1, 1, 59, tzinfo=_NY, fold=0),
        dt.datetime(2020, 11, 1, 1, 1, tzinfo=_NY, fold=1),
        timezones=st.just(_NY),
    )
    check_roundtrip_many(strategy, data)


def test_aware_datetimes_roundtrip_both_folds():
    strategy = st.datetimes(
        dt.datetime(2020, 1, 1, tzinfo=_NY),
        dt.datetime(2021, 1, 1, tzinfo=_NY),
        timezones=st.just(_NY),
    )
    # 2020-11-01 01:30 occurs twice in America/New_York
    for fold in (0, 1):
        value = dt.datetime(2020, 11, 1, 1, 30, tzinfo=_NY, fold=fold)
        assert strategy._invert(value) == (2020, 11, 1, 1, 30, 0, 0, fold)
        assert_roundtrip(strategy, value)


def test_aware_datetimes_utc_frame_encodes_utc_wall_time():
    strategy = st.datetimes(
        dt.datetime(2020, 11, 1, 1, 59, tzinfo=_NY, fold=0),
        dt.datetime(2020, 11, 1, 1, 1, tzinfo=_NY, fold=1),
        timezones=st.just(_NY),
    )
    value = dt.datetime(2020, 11, 1, 1, 59, 30, tzinfo=_NY, fold=0)  # 05:59:30 UTC
    assert strategy._invert(value) == (2020, 11, 1, 5, 59, 30, 0, 0)


def test_aware_datetimes_reproduce_imaginary_values_in_wall_clock_frame():
    strategy = st.datetimes(
        dt.datetime(2024, 1, 1, tzinfo=_NY),
        dt.datetime(2025, 1, 1, tzinfo=_NY),
        timezones=st.just(_NY),
    )
    # 2024-03-10 02:30 New York is in the imaginary DST gap
    assert_roundtrip(strategy, dt.datetime(2024, 3, 10, 2, 30, tzinfo=_NY))


@given(st.data())
def test_aware_datetimes_with_default_timezones(data):
    strategy = st.datetimes(
        dt.datetime(2020, 1, 1, tzinfo=_UTC),
        dt.datetime(2021, 1, 1, tzinfo=_UTC),
    )
    check_roundtrip_many(strategy, data)


@given(st.data())
def test_timezone_keys(data):
    check_roundtrip_many(st.timezone_keys(), data)


@given(st.data())
def test_timezones(data):
    # inverting a ZoneInfo relies on instances being cached per key, so that
    # plain == (which ZoneInfo does not override) compares equal
    assert zoneinfo.ZoneInfo("America/New_York") is zoneinfo.ZoneInfo(
        "America/New_York"
    )
    check_roundtrip_many(st.timezones(), data)


def test_prefixed_timezone_keys_invert(monkeypatch):
    # This environment may not ship posix/ or right/ tzdata files, so treat
    # every key as valid: each prefix then forms its own one_of branch, whose
    # selector re-encodes - and shrinks - the prefix choice.
    import hypothesis.strategies._internal.datetime as dtmodule

    monkeypatch.setattr(dtmodule, "_valid_key_cacheable", lambda tzpath, key: True)
    branches = dtmodule._timezone_key_strategies(allow_prefix=True)
    assert len(branches) == 3
    strategy = one_of(branches)
    assert strategy._invert("UTC") == (0, 0)
    assert strategy._invert("posix/UTC") == (1, 0)
    assert strategy._invert("right/UTC") == (2, 0)
    assert_roundtrip(strategy, "posix/UTC")
    assert isinstance(strategy._invert("posix/no/such/zone"), Impossible)


def test_no_cache_timezones_do_not_invert():
    # ZoneInfo.no_cache instances compare by identity, so a fresh instance
    # per draw can never equal the value being inverted
    result = st.timezones(no_cache=True)._invert(zoneinfo.ZoneInfo("UTC"))
    assert isinstance(result, Impossible)


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
        (st.times(), dt.time(12, 0, tzinfo=dt.timezone.utc)),
        (st.times(min_value=dt.time(12, 0)), dt.time(6, 0)),
        (st.datetimes(), "not a datetime"),
        (st.datetimes(), dt.datetime(2020, 6, 1, tzinfo=dt.timezone.utc)),
        (st.datetimes(max_value=dt.datetime(2020, 1, 1)), dt.datetime(2025, 1, 1)),
        # a naive value into an aware-bounded strategy
        (
            st.datetimes(
                min_value=dt.datetime(2020, 1, 1, tzinfo=dt.timezone.utc),
                timezones=st.just(dt.timezone.utc),
            ),
            dt.datetime(2020, 6, 1),
        ),
        # an instant outside the aware bounds
        (
            st.datetimes(
                max_value=dt.datetime(2020, 1, 1, tzinfo=dt.timezone.utc),
                timezones=st.just(dt.timezone.utc),
            ),
            dt.datetime(2025, 1, 1, tzinfo=dt.timezone.utc),
        ),
        # a timezone the timezones strategy cannot produce
        (
            st.datetimes(
                min_value=dt.datetime(2020, 1, 1, tzinfo=dt.timezone.utc),
                timezones=st.just(dt.timezone.utc),
            ),
            dt.datetime(2020, 6, 1, tzinfo=dt.timezone(dt.timedelta(hours=1))),
        ),
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
        # an imaginary value inside aware instant bounds
        (
            st.datetimes(
                dt.datetime(2024, 1, 1, tzinfo=_NY),
                dt.datetime(2025, 1, 1, tzinfo=_NY),
                timezones=st.just(_NY),
                allow_imaginary=False,
            ),
            dt.datetime(2024, 3, 10, 2, 30, tzinfo=_NY),
        ),
        # inside the instant bounds, but outside the wall-clock drawing window
        (
            st.datetimes(
                dt.datetime(2020, 10, 30, 12, tzinfo=_NY),
                dt.datetime(2020, 11, 1, 1, 15, fold=1, tzinfo=_NY),
                timezones=st.just(_NY),
            ),
            dt.datetime(2020, 11, 1, 1, 30, tzinfo=_NY),
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
        (st.builds(_Pair, x=st.integers(), y=st.integers()), _Pair("bad", 2)),
        (st.tuples(st.integers()), ("not an int",)),
        (st.lists(st.nothing()), [1]),
        (st.lists(st.sampled_from([1, 2, 3]), unique=True), "not a list"),
        (st.lists(st.sampled_from([1, 2, 3]), unique=True, min_size=2), [1]),
        (st.dictionaries(st.sampled_from([1, 2, 3]), st.integers()), {1: "x"}),
        (st.fixed_dictionaries({"a": st.integers()}), "not a dict"),
        (
            st.fixed_dictionaries({"a": st.booleans()}, optional={"b": st.integers()}),
            {"a": True, "b": "not an int"},
        ),
    ],
)
def test_out_of_image_is_impossible(strategy, value):
    assert isinstance(strategy._invert(value), Impossible)


@pytest.mark.parametrize(
    "strategy,value",
    [
        # a tzinfo whose utcoffset() raises cannot be classified at all
        (
            st.datetimes(
                dt.datetime(2020, 1, 1, tzinfo=_UTC),
                dt.datetime(2021, 1, 1, tzinfo=_UTC),
                timezones=st.just(_UTC),
            ),
            dt.datetime(2020, 6, 1, tzinfo=_RaisingTzinfo()),
        ),
        # a raising uniqueness key proves nothing about the value
        (st.lists(st.integers(), unique_by=lambda x: x.key), [1, 2]),
    ],
)
def test_unclassifiable_values_give_holes(strategy, value):
    result = strategy._invert(value)
    assert any(isinstance(c, ValueHole) for c in result)


def test_empty_element_strategy_inverts_only_the_empty_list():
    assert st.lists(st.nothing())._invert([]) == ()


def test_unique_list_with_tuple_suffixes_rejects_malformed_values():
    # dictionaries() maps dict over a unique list of (key, value) pairs; go
    # through the inner list strategy directly to check its shape guards.
    dicts = st.dictionaries(st.integers(), st.integers())
    inner = dicts.wrapped_strategy.wrapped_strategy.mapped_strategy
    assert isinstance(inner._invert("not a list"), Impossible)
    assert isinstance(inner._invert([1, 2]), Impossible)
    # and likewise for the pool-indexed variant used with sampled_from keys
    sampled = st.dictionaries(st.sampled_from([1, 2, 3]), st.integers())
    inner = sampled.wrapped_strategy.wrapped_strategy.mapped_strategy
    assert isinstance(inner._invert([1, 2]), Impossible)


def test_aware_datetimes_with_unrepresentable_bound_cannot_invert():
    # every wall time representable in UTC-00:30 is after this strategy's
    # maximum instant, so no drawing window exists in that timezone
    strategy = st.datetimes(
        dt.datetime(1, 1, 1, 0, 0, tzinfo=dt.timezone.utc),
        dt.datetime(1, 1, 1, 0, 20, tzinfo=dt.timezone.utc),
        timezones=st.just(dt.timezone.utc),
    ).wrapped_strategy
    tz = dt.timezone(-dt.timedelta(minutes=30))
    value = dt.datetime(1, 1, 1, 0, 10, tzinfo=dt.timezone.utc)
    assert isinstance(
        strategy._invert_aware_fields(value, tz, imaginary=False), Impossible
    )


# Bounds inside the same DST fold are in inverted wall-clock order, so this
# strategy draws in the UTC frame; see the roundtrip test of the same name.
_utc_frame_strategy = st.datetimes(
    dt.datetime(2020, 11, 1, 1, 59, tzinfo=_NY, fold=0),
    dt.datetime(2020, 11, 1, 1, 1, tzinfo=_NY, fold=1),
    timezones=st.just(_NY),
).wrapped_strategy


def test_utc_frame_cannot_encode_imaginary_values():
    value = dt.datetime(2020, 11, 1, 1, 30, tzinfo=_NY)
    result = _utc_frame_strategy._invert_aware_fields(value, _NY, imaginary=True)
    assert isinstance(result, Impossible)


def test_utc_frame_cannot_encode_values_which_overflow_utc():
    value = dt.datetime.max.replace(tzinfo=dt.timezone(-dt.timedelta(hours=1)))
    result = _utc_frame_strategy._invert_aware_fields(value, _NY, imaginary=False)
    assert isinstance(result, Impossible)


@pytest.mark.parametrize(
    "strategy,value",
    [
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
def test_unimplemented_inversions_give_holes(strategy, value):
    result = strategy._invert(value)
    assert any(isinstance(c, ValueHole) for c in result)


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


def test_type_confusions_are_distinguished_at_top_level():
    # equal_values requires exact types, so equal-comparing values of
    # different types invert to their own element, not each other's
    assert st.sampled_from([1, True])._invert(True) == (1,)
    assert st.sampled_from([1, True])._invert(1) == (0,)
    assert st.sampled_from([0.0, -0.0])._invert(-0.0) == (1,)
    assert st.sampled_from([2, math.nan])._invert(math.nan) == (1,)


def test_nested_values_compare_elementwise_in_lists_and_tuples():
    # distinct nan objects, so container == cannot succeed via identity
    assert st.just([float("nan")])._invert([float("nan")]) == ()
    assert st.sampled_from([(1,), (True,)])._invert((True,)) == (1,)


@pytest.mark.skipif(
    PYPY, reason="unboxed float storage compares container nans bitwise"
)
def test_nested_nan_in_other_containers_is_not_matched():
    # equal_values falls back to plain == inside dicts and sets, where a
    # (non-identical) NaN compares unequal; a conservative miss, caught by
    # replay verification
    assert isinstance(
        st.just({"a": float("nan")})._invert({"a": float("nan")}), Impossible
    )
    nan_set = frozenset([float("nan")])
    assert isinstance(st.just(nan_set)._invert(frozenset([float("nan")])), Impossible)


def test_impossible_notes_the_path_to_the_failure():
    result = st.lists(st.lists(st.integers()))._invert([[1], ["a"]])
    assert isinstance(result, Impossible)
    assert result.cause[0] == "'a' is not an integer"
    assert any("at index 0 of ['a']" in note for note in result.cause)
    assert any("at index 1 of [[1], ['a']]" in note for note in result.cause)


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


def test_transformations_which_draw_leave_holes_unclaimed():
    # e.g. stateful rule filters draw feature flags; a hole cannot be claimed
    # by executing such draws, and degrades to a misalignment instead of
    # corrupting the choice stream.
    data = ConjectureData.for_choices((ValueHole(2), True))
    strategy = st.sampled_from([1, 2, 3]).filter(lambda x: data.draw_boolean())
    with BuildContext(data, wrapped_test=lambda: None):
        assert data.draw(strategy) == 1
    assert data.misaligned_at is not None


def _hole_for(strategy, value):
    # the hole an unanalysable strategy leaves for value: default fields,
    # with the cause its _invert actually produces
    return ValueHole(
        value,
        strategy=unwrap_strategies(strategy),
        cause=f"cannot invert {strategy!r} (value={value!r})",
    )


_mapped_chr = st.integers().map(chr)


def test_holes_stand_in_for_unencodable_elements():
    strategy = st.tuples(st.integers(), _mapped_chr, st.booleans())
    expected = (1, _hole_for(_mapped_chr, "2"), True)
    assert strategy._invert((1, "2", True)) == expected


def test_lists_leave_one_hole_per_unencodable_element():
    # not `x * 2`: lambdas AST-identical to test_lambda_formatting's temp-file
    # specimens would pollute the shared lambda-description digest cache
    doubled = st.integers().map(lambda x: x + x)
    strategy = st.lists(doubled)
    expected = (True, _hole_for(doubled, 2), True, _hole_for(doubled, 4), False)
    assert strategy._invert([2, 4]) == expected


def test_nested_structure_stays_concrete_around_holes():
    strategy = st.lists(st.tuples(st.integers(), _mapped_chr))
    expected = (True, 1, _hole_for(_mapped_chr, "2"), False)
    assert strategy._invert([(1, "2")]) == expected


def test_an_unanalysable_map_is_a_single_hole():
    assert _mapped_chr._invert("5") == (_hole_for(_mapped_chr, "5"),)
    (h,) = _mapped_chr._invert("5")
    assert h.strategy is _mapped_chr.wrapped_strategy  # the reified MappedStrategy


def test_one_of_with_only_unknown_branches_is_one_hole():
    strategy = st.integers() | st.text().map(str.upper)
    assert strategy._invert(5) == (0, 5)
    # integers() is Impossible for "ABC" and the map branch is a bare hole,
    # which encodes nothing and so is not kept as a candidate
    expected = ValueHole(
        "ABC",
        strategy=strategy,
        cause=f"'ABC' is not produced by any branch of {strategy!r}",
    )
    assert strategy._invert("ABC") == (expected,)


def test_one_of_holes_carry_partial_branch_candidates():
    strategy = st.booleans() | st.lists(_mapped_chr)
    expected = ValueHole(
        ["1"],
        strategy=strategy,
        candidates=((1, True, _hole_for(_mapped_chr, "1"), False),),
        cause=f"['1'] is not produced by any branch of {strategy!r}",
    )
    assert strategy._invert(["1"]) == (expected,)


def test_one_of_keeps_every_partial_branch_candidate():
    branches = [st.tuples(st.booleans(), st.integers().map(chr)) for _ in range(5)]
    (h,) = one_of(branches)._invert((True, "1"))
    assert [candidate[0] for candidate in h.candidates] == [0, 1, 2, 3, 4]


def test_one_of_of_only_impossible_branches_is_impossible():
    strategy = st.booleans() | st.integers()
    assert strategy._invert("text") == Impossible(
        f"'text' is not produced by any branch of {strategy!r}"
    )


def test_fixed_dictionaries_keep_concrete_values_around_holes():
    strategy = st.fixed_dictionaries({"a": st.integers(), "b": _mapped_chr})
    value = {"a": 1, "b": "2"}
    # values in mapping order, then an identity shuffle of the pairs
    assert strategy._invert(value) == (1, _hole_for(_mapped_chr, "2"), 0)
    assert st.fixed_dictionaries({"a": st.integers()})._invert(
        {"mismatched": 1}
    ) == Impossible(
        f"{ {'mismatched': 1} !r} has the wrong keys for "
        f"{unwrap_strategies(st.fixed_dictionaries({'a': st.integers()}))!r}"
    )


def test_builds_keeps_concrete_fields_around_holes():
    strategy = st.builds(_Pair, x=st.integers(), y=_mapped_chr)
    assert strategy._invert(_Pair(1, "2")) == (1, _hole_for(_mapped_chr, "2"))


def test_filters_pass_holes_through():
    strategy = st.lists(_mapped_chr).filter(len)
    assert strategy._invert(["1"]) == (True, _hole_for(_mapped_chr, "1"), False)
    # .filter(len) is rewritten into a min_size=1 bound, which [] violates
    assert strategy._invert([]) == Impossible(
        f"len=0 outside [1, inf] for {unwrap_strategies(strategy)!r}"
    )


def test_failing_filter_predicates_are_impossible():
    strategy = st.integers().filter(lambda x: x % 2 == 0)
    assert strategy._invert(3) == Impossible(
        f"3 does not satisfy filter {unwrap_strategies(strategy)!r}"
    )


def test_shape_and_uniqueness_violations_are_impossible():
    strategy = st.tuples(st.integers())
    assert strategy._invert("not a tuple") == Impossible(
        "'not a tuple' is not a tuple of length 1"
    )
    strategy = st.lists(st.integers(), max_size=1)
    assert strategy._invert([1, 2]) == Impossible(
        f"len=2 outside [0, 1] for {unwrap_strategies(strategy)!r}"
    )
    strategy = st.lists(st.integers(), unique=True)
    assert strategy._invert([1, 1]) == Impossible(
        f"[1, 1] has duplicate keys for {unwrap_strategies(strategy)!r}"
    )


def test_child_impossible_makes_the_parent_impossible():
    strategy = st.tuples(st.booleans())
    assert strategy._invert(("nope",)) == Impossible(
        "'nope' is not a bool",
        f"at index 0 of ('nope',), strategy={unwrap_strategies(strategy)!r}",
    )
    # ...but an unknown child keeps the parent a partial encoding
    strategy = st.tuples(st.booleans(), _mapped_chr)
    assert strategy._invert((True, "1")) == (True, _hole_for(_mapped_chr, "1"))


def test_impossible_composes_path_context():
    result = st.tuples(st.booleans(), st.integers(), st.booleans())._invert(
        (True, "five", False)
    )
    assert isinstance(result, Impossible)
    assert result.cause[0] == "'five' is not an integer"
    assert result.cause[1].startswith("at index 1 of (True, 'five', False)")


def test_impossible_with_note_appends_to_the_cause():
    assert Impossible("no").with_note("here") == Impossible("no", "here")
    assert Impossible("no").with_note("here").cause == ("no", "here")


def test_raising_filter_predicates_give_a_hole_not_impossible():
    strategy = st.integers().filter(lambda x: x.bit_length() > "3")
    (h,) = strategy._invert(5)
    assert isinstance(h, ValueHole)


def test_hole_budget_aborts_pathological_inversions():
    # armed only at the draw-time claim site; direct calls are unlimited
    value = [str(i) for i in range(HOLE_LIMIT + 1)]
    _hole_budget.remaining = HOLE_LIMIT
    try:
        with pytest.raises(InvertAborted):
            st.lists(st.integers().map(chr))._invert(value)
    finally:
        _hole_budget.remaining = None
    assert st.integers()._invert(5) == (5,)


_ID_PREFIX = "id-"
_ID_TEMPLATE = "id-{0}"


def _parenthesize(s):
    return "(" + s + ")"


@pytest.mark.parametrize(
    "strategy,value,expected",
    [
        # constant-prefix/suffix concatenation
        (st.text().map(lambda s: "pre-" + s), "pre-xyz", ("xyz",)),
        (st.text().map(lambda s: s + "-post"), "xyz-post", ("xyz",)),
        (st.text().map(lambda s: "a" + s + "b"), "aXb", ("X",)),
        # constants may come from globals, closures, or named functions
        (st.text().map(lambda s: _ID_PREFIX + s), "id-x", ("x",)),
        (st.text().map(_parenthesize), "(deep)", ("deep",)),
        # single-field formatting, in all its spellings
        (st.text().map("id-{}".format), "id-dragon", ("dragon",)),
        (st.text().map("{}!".format), "ok!", ("ok",)),
        (st.text().map(_ID_TEMPLATE.format), "id-x", ("x",)),
        (st.text().map(lambda s: f"id-{s}"), "id-x", ("x",)),
        (st.text().map(lambda s: _ID_TEMPLATE.format(s)), "id-x", ("x",)),
        # a formatted field parses back to non-string preimages too
        (st.integers().map(lambda n: f"n={n}"), "n=5", (5,)),
        (st.integers().map("v{}".format), "v7", (7,)),
        (st.booleans().map("{}?".format), "True?", (True,)),
        # str() and repr() are the trivial template: parse the whole value back
        (st.integers().map(str), "17", (17,)),
        (st.booleans().map(str), "True", (True,)),
        (st.lists(st.integers()).map(str), "[1, 2]", (True, 1, True, 2, False)),
        (st.text().map(str), "abc", ("abc",)),
        (st.integers().map(repr), "17", (17,)),
        (st.text().map(repr), "'abc'", ("abc",)),
        (st.lists(st.integers()).map(repr), "[1, 2]", (True, 1, True, 2, False)),
        # nested maps invert innermost-last
        (st.text().map(lambda s: "a" + s).map(lambda s: "b" + s), "baX", ("X",)),
        # inside a union, giving cross-branch re-encoding of mapped strings
        (
            st.text().map(lambda s: "id-" + s) | st.sampled_from(["id-a", "id-b"]),
            "id-b",
            (0, "b"),
        ),
    ],
)
def test_string_pack_inversion(strategy, value, expected):
    assert strategy._invert(value) == expected
    assert_roundtrip(strategy, value)


def test_closure_constants_resolve():
    prefix = "pre|"
    strategy = st.text().map(lambda s: prefix + s)
    assert strategy._invert("pre|abc") == ("abc",)
    assert_roundtrip(strategy, "pre|abc")


@pytest.mark.parametrize(
    "strategy,value",
    [
        # a fully-understood template whose constant text is absent
        (st.text().map(lambda s: "pre-" + s), "wrong-prefix"),
        (st.text().map(lambda s: s + "!"), "no-bang"),
        (st.text().map("id-{}".format), "wrong-prefix"),
        # concatenation has exactly one preimage, and the inner strategy
        # proves it impossible
        (st.text(max_size=2).map(lambda s: "pre-" + s), "pre-toolong"),
        # nothing verifies: repr of the raw string adds quotes, and
        # literal_eval cannot parse the value
        (st.integers().map(repr), "not an int"),
        # a string-template pack of a non-dict is not analysed for dict packs
        (st.dictionaries(st.text(), st.integers()), [("a", 1)]),
    ],
)
def test_string_packs_which_are_provably_impossible(strategy, value):
    assert isinstance(strategy._invert(value), Impossible)


@pytest.mark.parametrize(
    "strategy,value",
    [
        # unsupported pack shapes: case ops, str(), %-templates, string
        # methods, multiple or spec-carrying fields
        (st.text().map(str.upper), "ABC"),
        (st.text().map(lambda s: "%s!" % s), "x!"),  # noqa: UP031
        (st.text().map(lambda s: s.replace("a", "b")), "b"),
        (st.text().map(lambda s: s.zfill(3)), "00x"),
        (st.text().map(lambda s: ",".join([s])), "x"),  # noqa: FLY002
        (st.text().map(lambda s: f"{s}{s}"), "xx"),
        (st.text().map(lambda s: f"{s:>3}"), "  x"),
        # a formatted field whose verified preimage the inner strategy
        # rejects: the parse candidates are not exhaustive, so no proof
        (st.integers().map("v{}".format), "vnot-an-int"),
        (st.integers().map(str), "not an int"),
        (st.integers().map(repr), "'abc'"),
    ],
)
def test_unanalysable_string_packs_give_a_hole(strategy, value):
    result = strategy._invert(value)
    assert any(isinstance(c, ValueHole) for c in result)


def test_string_pack_keeps_verified_preimage_as_candidate():
    # the preimage "A" is verified against the outer pack, but the inner
    # .map(chr) cannot encode it - so it survives as a partial candidate
    strategy = st.integers().map(chr).map(lambda s: "x" + s)
    (h,) = strategy._invert("xA")
    assert h.value == "xA"
    ((inner,),) = h.candidates
    assert isinstance(inner, ValueHole)
    assert inner.value == "A"


def _multi_statement_pack(s):
    assert isinstance(s, str)
    return "p" + s


def _bare_return_pack(s):
    return


async def _async_pack(s):
    return "p" + s


_exec_ns: dict = {}
exec("def _exec_pack(s): return 'p' + s", _exec_ns)


def _documented_pack(s):
    """Prefix the argument."""
    return "doc-" + s


def test_def_pack_with_docstring_inverts():
    assert_roundtrip(st.text().map(_documented_pack), "doc-x")


@pytest.mark.parametrize(
    "fn",
    [
        "{".format,  # malformed template
        "{!r}".format,  # unsupported conversion
        lambda s: s.strip() + "!",  # unsupported concatenation segment
        lambda s: ("a" + "b").format(s),  # template is not a resolvable constant
        eval("lambda s: 'p' + s"),  # no source available for the lambda
        _exec_ns["_exec_pack"],  # no source available for the def
        _async_pack,  # not a plain function body
        _bare_return_pack,  # returns nothing
        lambda a, b: "ab",  # wrong arity
        _multi_statement_pack,
    ],
)
def test_unanalysable_pack_shapes_have_no_template(fn):
    assert string_template(fn) is None


def test_a_raising_pack_fails_verification():
    strategy = st.text().map(lambda s: "p" + s).wrapped_strategy
    assert strategy._packs_to("x", "px")
    assert not strategy._packs_to(123, "p123")
