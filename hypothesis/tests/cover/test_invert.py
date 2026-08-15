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
from hypothesis.internal.compat import PYPY
from hypothesis.internal.conjecture.choice import ValueHole, choice_equal
from hypothesis.internal.conjecture.data import ConjectureData
from hypothesis.internal.conjecture.junkdrawer import equal_values
from hypothesis.strategies._internal.lazy import LazyStrategy
from hypothesis.strategies._internal.strategies import one_of

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
def test_one_of_with_a_single_branch(data):
    check_roundtrip_many(st.integers() | st.nothing(), data)


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
    with pytest.raises(CannotInvert):
        strategy._invert("posix/no/such/zone")


def test_no_cache_timezones_do_not_invert():
    # ZoneInfo.no_cache instances compare by identity, so a fresh instance
    # per draw can never equal the value being inverted
    with pytest.raises(CannotInvert):
        st.timezones(no_cache=True)._invert(zoneinfo.ZoneInfo("UTC"))


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
        # a tzinfo whose utcoffset() raises cannot be located at all
        (
            st.datetimes(
                dt.datetime(2020, 1, 1, tzinfo=_UTC),
                dt.datetime(2021, 1, 1, tzinfo=_UTC),
                timezones=st.just(_UTC),
            ),
            dt.datetime(2020, 6, 1, tzinfo=_RaisingTzinfo()),
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
        (st.lists(st.integers(), unique_by=lambda x: x.key), [1, 2]),
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
def test_out_of_image_raises(strategy, value):
    with pytest.raises(CannotInvert):
        strategy._invert(value)


def test_empty_element_strategy_inverts_only_the_empty_list():
    assert st.lists(st.nothing())._invert([]) == ()


def test_unique_list_with_tuple_suffixes_rejects_malformed_values():
    # dictionaries() maps dict over a unique list of (key, value) pairs; go
    # through the inner list strategy directly to check its shape guards.
    dicts = st.dictionaries(st.integers(), st.integers())
    inner = dicts.wrapped_strategy.wrapped_strategy.mapped_strategy
    with pytest.raises(CannotInvert):
        inner._invert("not a list")
    with pytest.raises(CannotInvert):
        inner._invert([1, 2])


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
    with pytest.raises(CannotInvert):
        strategy._invert_aware_fields(value, tz, imaginary=False)


# Bounds inside the same DST fold are in inverted wall-clock order, so this
# strategy draws in the UTC frame; see the roundtrip test of the same name.
_utc_frame_strategy = st.datetimes(
    dt.datetime(2020, 11, 1, 1, 59, tzinfo=_NY, fold=0),
    dt.datetime(2020, 11, 1, 1, 1, tzinfo=_NY, fold=1),
    timezones=st.just(_NY),
).wrapped_strategy


def test_utc_frame_cannot_encode_imaginary_values():
    value = dt.datetime(2020, 11, 1, 1, 30, tzinfo=_NY)
    with pytest.raises(CannotInvert):
        _utc_frame_strategy._invert_aware_fields(value, _NY, imaginary=True)


def test_utc_frame_cannot_encode_values_which_overflow_utc():
    value = dt.datetime.max.replace(tzinfo=dt.timezone(-dt.timedelta(hours=1)))
    with pytest.raises(CannotInvert):
        _utc_frame_strategy._invert_aware_fields(value, _NY, imaginary=False)


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
    with pytest.raises(CannotInvert):
        st.just({"a": float("nan")})._invert({"a": float("nan")})
    with pytest.raises(CannotInvert):
        st.just(frozenset([float("nan")]))._invert(frozenset([float("nan")]))


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


def test_transformations_which_draw_cannot_invert():
    # e.g. stateful rule filters draw feature flags; a hole cannot be claimed
    # by executing such draws, and degrades to a misalignment instead of
    # corrupting the choice stream.
    data = ConjectureData.for_choices((ValueHole(2), True))
    strategy = st.sampled_from([1, 2, 3]).filter(lambda x: data.draw_boolean())
    with BuildContext(data, wrapped_test=lambda: None):
        assert data.draw(strategy) == 1
    assert data.misaligned_at is not None
