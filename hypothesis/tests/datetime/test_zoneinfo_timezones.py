# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import datetime as dt
import platform
import zoneinfo

import pytest

from hypothesis import given, settings, strategies as st
from hypothesis.errors import InvalidArgument
from hypothesis.strategies._internal.datetime import _instant

from tests.common.debug import (
    assert_all_examples,
    assert_no_examples,
    find_any,
    minimal,
)


def test_utc_is_minimal():
    assert minimal(st.timezones()) is zoneinfo.ZoneInfo("UTC")


def test_can_generate_non_utc():
    find_any(
        st.datetimes(timezones=st.timezones()).filter(lambda d: d.tzinfo.key != "UTC")
    )


@given(st.data(), st.datetimes(), st.datetimes())
def test_datetimes_stay_within_naive_bounds(data, lo, hi):
    if lo > hi:
        lo, hi = hi, lo
    out = data.draw(st.datetimes(lo, hi, timezones=st.timezones()))
    assert lo <= out.replace(tzinfo=None) <= hi


@given(
    st.data(),
    st.datetimes(timezones=st.timezones()),
    st.datetimes(timezones=st.timezones()),
)
def test_datetimes_stay_within_aware_bounds(data, lo, hi):
    if _instant(lo) > _instant(hi):
        lo, hi = hi, lo
    # timezones defaults to st.timezones() when the bounds are aware
    out = data.draw(st.datetimes(lo, hi))
    assert isinstance(out.tzinfo, zoneinfo.ZoneInfo)
    assert _instant(lo) <= _instant(out) <= _instant(hi)


@given(
    st.datetimes(
        min_value=dt.datetime(2025, 1, 1, tzinfo=dt.timezone.utc), allow_imaginary=False
    )
)
def test_allow_imaginary_is_not_an_error_for_aware_bounds(d):
    pass


# America/New_York fell back from 02:00 EDT to 01:00 EST on 2020-11-01, and
# Europe/Dublin - which has a negative DST offset - from 02:00 UTC+1 to 01:00 GMT
# on 2020-10-25; in both, wall times between 01:00 and 02:00 are ambiguous.
FALL_BACK_DAYS = [
    ("America/New_York", dt.date(2020, 11, 1)),
    ("Europe/Dublin", dt.date(2020, 10, 25)),
]


def at(day, hour, minute=0, *, key, fold=0):
    tzinfo = zoneinfo.ZoneInfo(key)
    return dt.datetime.combine(day, dt.time(hour, minute, fold=fold), tzinfo=tzinfo)


@pytest.mark.parametrize("key, day", FALL_BACK_DAYS)
def test_bounds_at_either_side_of_a_fold(key, day):
    lo = at(day, 1, 30, key=key, fold=1)
    hi = at(day, 3, key=key)
    # Wall times up to an hour after lo are ambiguous: with fold=0 they would
    # be moments before it, so the strategy must constrain the fold to 1.
    assert_all_examples(
        st.datetimes(lo, hi, timezones=st.just(lo.tzinfo)),
        lambda d: _instant(lo) <= _instant(d) <= _instant(hi),
    )
    lo2 = at(day, 0, key=key)
    hi2 = at(day, 1, 45, key=key, fold=0)
    assert_all_examples(
        st.datetimes(lo2, hi2, timezones=st.just(lo.tzinfo)),
        lambda d: _instant(lo2) <= _instant(d) <= _instant(hi2),
    )


@pytest.mark.parametrize("key, day", FALL_BACK_DAYS)
def test_fold_bound_with_long_interval(key, day):
    # Intervals of more than a day are drawn as local wall times, rejecting
    # the rare draw of an ambiguous time beside a bound with the out-of-bounds
    # fold - rather than the draw-in-UTC approach for shorter intervals.
    lo = at(day, 1, 30, key=key, fold=1)
    hi = at(day + dt.timedelta(days=3), 3, key=key)
    assert_all_examples(
        st.datetimes(lo, hi, timezones=st.just(lo.tzinfo)),
        lambda d: _instant(lo) <= _instant(d) <= _instant(hi),
        settings=settings(max_examples=300),
    )


@pytest.mark.parametrize("key, day", FALL_BACK_DAYS)
def test_bounds_inside_a_fold(key, day):
    lo = at(day, 1, 55, key=key, fold=0)
    hi = at(day, 1, 5, key=key, fold=1)
    # ...so lo is an earlier moment than hi, but a later wall-clock time!
    assert _instant(lo) < _instant(hi)
    assert lo.replace(tzinfo=None) > hi.replace(tzinfo=None)
    strategy = st.datetimes(lo, hi, timezones=st.just(lo.tzinfo))
    assert_all_examples(strategy, lambda d: _instant(lo) <= _instant(d) <= _instant(hi))
    find_any(strategy, lambda d: d.fold == 0)
    find_any(strategy, lambda d: d.fold == 1)


@pytest.mark.parametrize("key, day", FALL_BACK_DAYS)
def test_fold_inverted_bounds_are_invalid(key, day):
    # fold=1 is the later moment, so these bounds are ordered by wall clock time, but not
    # by UTC (_instant) time. This ordering should be rejected.
    lo = at(day, 1, 45, key=key, fold=1)
    hi = at(day, 1, 50, key=key, fold=0)
    assert lo.replace(tzinfo=None) < hi.replace(tzinfo=None)
    assert _instant(hi) < _instant(lo)
    with pytest.raises(InvalidArgument):
        st.datetimes(lo, hi, timezones=st.just(lo.tzinfo)).validate()


@pytest.mark.parametrize("key, day", FALL_BACK_DAYS)
def test_equal_bounds_at_ambiguous_moment_preserves_fold(key, day):
    dt = at(day, 1, 30, key=key, fold=1)
    assert_all_examples(
        st.datetimes(dt, dt, timezones=st.just(dt.tzinfo)),
        lambda d: _instant(d) == _instant(dt) and d.fold == 1,
    )


@pytest.mark.parametrize("kwargs", [{"no_cache": 1}])
def test_timezones_argument_validation(kwargs):
    with pytest.raises(InvalidArgument):
        st.timezones(**kwargs).validate()


@pytest.mark.parametrize(
    "kwargs",
    [
        # {"allow_alias": 1},
        # {"allow_deprecated": 1},
        {"allow_prefix": 1},
    ],
)
def test_timezone_keys_argument_validation(kwargs):
    with pytest.raises(InvalidArgument):
        st.timezone_keys(**kwargs).validate()


@pytest.mark.xfail(strict=False, reason="newly failing on GitHub Actions")
@pytest.mark.skipif(platform.system() != "Linux", reason="platform-specific")
def test_can_generate_prefixes_if_allowed_and_available():
    """
    This is actually kinda fiddly: we may generate timezone keys with the
    "posix/" or "right/" prefix if-and-only-if they are present on the filesystem.

    This immediately rules out Windows (which uses the tzdata package instead),
    along with OSX (which doesn't seem to have prefixed keys).  We believe that
    they are present on at least most Linux distros, but have not done exhaustive
    testing.

    It's fine to just patch this test out if it fails - passing in the
    Hypothesis CI demonstrates that the feature works on *some* systems.
    """
    find_any(st.timezone_keys(), lambda s: s.startswith("posix/"))
    find_any(st.timezone_keys(), lambda s: s.startswith("right/"))


def test_can_disallow_prefixes():
    assert_no_examples(
        st.timezone_keys(allow_prefix=False),
        lambda s: s.startswith(("posix/", "right/")),
    )
