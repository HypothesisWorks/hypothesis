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
import operator as op
import sys
import warnings
import zoneinfo
from functools import cache, lru_cache, partial
from importlib import resources
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any, overload

from hypothesis.errors import CannotInvert, InvalidArgument
from hypothesis.internal.conjecture.choice import ChoiceT
from hypothesis.internal.validation import check_type, check_valid_interval
from hypothesis.strategies._internal.core import sampled_from
from hypothesis.strategies._internal.lazy import unwrap_strategies
from hypothesis.strategies._internal.misc import just, none, nothing
from hypothesis.strategies._internal.strategies import (
    FilteredStrategy,
    OneOfStrategy,
    SampledFromStrategy,
    SearchStrategy,
    one_of,
)
from hypothesis.strategies._internal.utils import defines_strategy

if TYPE_CHECKING:
    from annotated_types import Timezone

    NaiveDatetime = Annotated[dt.datetime, Timezone(None)]
    AwareDatetime = Annotated[dt.datetime, Timezone(...)]
elif at := sys.modules.get("annotated_types"):
    NaiveDatetime = Annotated[dt.datetime, at.Timezone(None)]
    AwareDatetime = Annotated[dt.datetime, at.Timezone(...)]
else:
    NaiveDatetime = AwareDatetime = dt.datetime

DATENAMES = ("year", "month", "day")
TIMENAMES = ("hour", "minute", "second", "microsecond")

_MICROSECOND = dt.timedelta(microseconds=1)


def _comparator_bound(condition):
    """Return ``(op, bound)`` for filter conditions like ``partial(op, bound)``,
    with a single positional argument to one of the five comparison operators."""
    if (
        isinstance(condition, partial)
        and len(condition.args) == 1
        and not condition.keywords
        and condition.func in (op.lt, op.le, op.eq, op.ge, op.gt)
    ):
        return condition.func, condition.args[0]
    return None


def _narrowed_bounds(func, arg, min_value, max_value, shift):
    """Narrow [min_value, max_value] to satisfy the condition ``func(arg, x)``.

    ``shift(value, steps)`` moves value by that many of the smallest representable
    steps, raising OverflowError if the result would be unrepresentable.  Returns
    the narrowed (min_value, max_value), or None if no values can satisfy the
    condition.
    """
    if func in (op.lt, op.gt):
        try:
            arg = shift(arg, 1 if func is op.lt else -1)
        except OverflowError:  # gt the maximum value, or lt the minimum
            return None
    lo, hi = {
        # We're talking about op(arg, x) - the reverse of our usual intuition!
        op.lt: (arg, max_value),  # lambda x: arg < x
        op.le: (arg, max_value),  # lambda x: arg <= x
        op.eq: (arg, arg),  #       lambda x: arg == x
        op.ge: (min_value, arg),  # lambda x: arg >= x
        op.gt: (min_value, arg),  # lambda x: arg > x
    }[func]
    lo = max(lo, min_value)
    hi = min(hi, max_value)
    if hi < lo:
        return None
    return lo, hi


def _timezones_kind(strat):
    """Classify the values a timezones= strategy can generate: "none" if only
    None, "aware" if only tzinfo instances, or "unknown" if we can't tell."""
    strat = unwrap_strategies(strat)
    if isinstance(strat, SampledFromStrategy) and all(
        name == "filter" for name, _ in strat._transformations
    ):
        kinds = {
            "none" if e is None else "aware" if isinstance(e, dt.tzinfo) else "unknown"
            for e in strat.elements
        }
        return kinds.pop() if len(kinds) == 1 else "unknown"
    if isinstance(strat, OneOfStrategy):
        kinds = {_timezones_kind(s) for s in strat.original_strategies}
        return kinds.pop() if len(kinds) == 1 else "unknown"
    return "unknown"


def is_pytz_timezone(tz):
    if not isinstance(tz, dt.tzinfo):
        return False
    module = type(tz).__module__
    return module == "pytz" or module.startswith("pytz.")


def replace_tzinfo(value, timezone):
    if is_pytz_timezone(timezone):
        # Pytz timezones are a little complicated, and using the .replace method
        # can cause some weird issues, so we use their special "localize" instead.
        #
        # We use the fold attribute as a convenient boolean for is_dst, even though
        # they're semantically distinct.  For ambiguous or imaginary hours, fold says
        # whether you should use the offset that applies before the gap (fold=0) or
        # the offset that applies after the gap (fold=1). is_dst says whether you
        # should choose the side that is "DST" or "STD" (STD->STD or DST->DST
        # transitions are unclear as you might expect).
        #
        # WARNING: this is INCORRECT for timezones with negative DST offsets such as
        #       "Europe/Dublin", but it's unclear what we could do instead beyond
        #       documenting the problem and recommending use of `dateutil` instead.
        return timezone.localize(value, is_dst=not value.fold)
    return value.replace(tzinfo=timezone)


def _instant(value):
    """A sort key ordering aware datetimes by the moment they refer to.

    Unlike comparison of datetimes which share a tzinfo - which falls back to
    ignoring both the timezone and the fold attribute - this respects the fold,
    and unlike .astimezone() it cannot overflow near datetime.min/max.
    """
    return value.replace(tzinfo=None) - dt.datetime.min - value.utcoffset()


def _ambiguous(value, tz):
    # Whether the naive value is inside a DST fold, i.e. is a wall time which
    # occurs twice in tz, so that its utcoffset depends on the fold attribute.
    return (
        replace_tzinfo(value.replace(fold=0), tz).utcoffset()
        != replace_tzinfo(value.replace(fold=1), tz).utcoffset()
    )


def datetime_does_not_exist(value):
    """This function tests whether the given datetime can be round-tripped to and
    from UTC.  It is an exact inverse of (and very similar to) the dateutil method
    https://dateutil.readthedocs.io/en/stable/tz.html#dateutil.tz.datetime_exists
    """
    # Naive datetimes cannot be imaginary, but we need this special case because
    # chaining .astimezone() ends with *the system local timezone*, not None.
    # See bug report in https://github.com/HypothesisWorks/hypothesis/issues/2662
    if value.tzinfo is None:
        return False
    try:
        # Does the naive portion of the datetime change when round-tripped to
        # UTC?  If so, or if this overflows, we say that it does not exist.
        roundtrip = value.astimezone(dt.timezone.utc).astimezone(value.tzinfo)
    except OverflowError:
        # Overflows at datetime.min or datetime.max boundary condition.
        # Rejecting these is acceptable, because timezones are close to
        # meaningless before ~1900 and subject to a lot of change by
        # 9999, so it should be a very small fraction of possible values.
        return True

    if (
        value.tzinfo is not roundtrip.tzinfo
        and value.utcoffset() != roundtrip.utcoffset()
    ):
        # This only ever occurs during imaginary (i.e. nonexistent) datetimes,
        # and only for pytz timezones which do not follow PEP-495 semantics.
        # (may exclude a few other edge cases, but you should use zoneinfo anyway)
        return True

    assert value.tzinfo is roundtrip.tzinfo, "so only the naive portions are compared"
    return value != roundtrip


def _num_days_in_month(year, month):
    """Branchless equivalent of ``monthrange(year, month)[1]`` for valid inputs.

    Written using only arithmetic and (in)equality, with no branching or indexing.
    This avoids concretizing the input or adding more path constraints than necessary.
    """
    leap = (year % 4 == 0) * (1 - (year % 100 == 0) * (year % 400 != 0))
    is_feb = month == 2
    is_30_day = 1 - (month != 4) * (month != 6) * (month != 9) * (month != 11)
    return 31 - is_30_day - is_feb * (3 - leap)


def draw_capped_multipart(
    data, min_value, max_value, duration_names=DATENAMES + TIMENAMES
):
    assert isinstance(min_value, (dt.date, dt.time, dt.datetime))
    assert type(min_value) == type(max_value)
    assert min_value <= max_value

    # cap_{low, high} records whether every field drawn so far has equalled
    # ``min_value``'s / ``max_value``'s, i.e. whether that bound is still "active" and
    # constrains the next field.
    #
    # cap_{low, high} are conceptually booleans. We define them as integers and interpret
    # boolean operations on them as multiplication, so that we don't concretize or
    # branch under symbolic backends. See
    # https://github.com/HypothesisWorks/hypothesis/issues/4759.
    cap_low = 1
    cap_high = 1
    result = {}
    for name in duration_names:
        natural_low = getattr(dt.datetime.min, name)
        if name == "day":
            natural_high = _num_days_in_month(result["year"], result["month"])
        else:
            natural_high = getattr(dt.datetime.max, name)
        # equivalent to:
        #   low  = min_value.<name> if cap_low  else natural_low
        #   high = max_value.<name> if cap_high else natural_high
        low = natural_low + cap_low * (getattr(min_value, name) - natural_low)
        high = natural_high + cap_high * (getattr(max_value, name) - natural_high)
        if name == "year":
            val = data.draw_integer(low, high, shrink_towards=2000)
        else:
            val = data.draw_integer(low, high)
        result[name] = val
        cap_low = cap_low * (val == low)
        cap_high = cap_high * (val == high)
    if hasattr(min_value, "fold"):
        # The `fold` attribute is ignored in comparison of naive datetimes.
        # In tz-aware datetimes it would require *very* invasive changes to
        # the logic above, and be very sensitive to the specific timezone
        # (at the cost of efficient shrinking and mutation), so at least for
        # now we stick with the status quo and generate it independently.
        result["fold"] = data.draw_integer(0, 1)
    return result


def _shift_datetime(value, steps):
    return value + steps * _MICROSECOND


# "Tricky" datetimes (https://github.com/HypothesisWorks/hypothesis/issues/69):
# with some probability we generate wall times at small offsets from an
# "interesting instant" - a moment at which the drawn timezone's
# (utcoffset, dst, tzname) triple changes, or a UTC leap second.  Working in
# the wall-clock frame means we hit imaginary times inside spring-forward
# gaps, ambiguous times (under both folds) inside fall-back folds, and the
# exact boundaries of each.

_SCAN_LO = dt.datetime(1800, 1, 1)  # tzdata's earliest transitions are ~1847
_SCAN_HI = dt.datetime(2050, 1, 1)  # beyond this, recurring rules just repeat
# The shortest gap between state changes anywhere in tzdata is just under
# seven days (Brazil moved the start of DST forward by a week in October
# 2000), so scanning at six-day resolution never puts two transitions in one
# window and therefore finds every transition of every zone; see the probing
# docstring below for what it would take to hide one from a future tzdata.
_PROBE_STEP = dt.timedelta(days=6)
_SECOND = dt.timedelta(seconds=1)
_FALLBACK_SCAN = dt.timedelta(days=4 * 366)  # covers any recurring annual rule
# The probability that a draw targets a tricky value, and the half-widths of
# the windows we draw them from: tight enough to hit the boundary
# microseconds, wide enough to reach e.g. the far side of a DST gap.
_TRICKY_P = 0.25
_TRICKY_WIDTHS = (
    dt.timedelta(seconds=1, microseconds=1),
    dt.timedelta(hours=1, microseconds=1),
    dt.timedelta(days=1),
)


# Naive datetimes for the UTC instant just after each change to TAI-UTC.
# Python datetimes cannot represent a leap second itself, but adjacent times
# are prime test cases for code which parses, formats, or smears them.
# Checked against the vendored IERS leap-seconds.list by a whole-repo test.
_LEAP_SECONDS = (
    dt.datetime(1972, 1, 1),
    dt.datetime(1972, 7, 1),
    dt.datetime(1973, 1, 1),
    dt.datetime(1974, 1, 1),
    dt.datetime(1975, 1, 1),
    dt.datetime(1976, 1, 1),
    dt.datetime(1977, 1, 1),
    dt.datetime(1978, 1, 1),
    dt.datetime(1979, 1, 1),
    dt.datetime(1980, 1, 1),
    dt.datetime(1981, 7, 1),
    dt.datetime(1982, 7, 1),
    dt.datetime(1983, 7, 1),
    dt.datetime(1985, 7, 1),
    dt.datetime(1988, 1, 1),
    dt.datetime(1990, 1, 1),
    dt.datetime(1991, 1, 1),
    dt.datetime(1992, 7, 1),
    dt.datetime(1993, 7, 1),
    dt.datetime(1994, 7, 1),
    dt.datetime(1996, 1, 1),
    dt.datetime(1997, 7, 1),
    dt.datetime(1999, 1, 1),
    dt.datetime(2006, 1, 1),
    dt.datetime(2009, 1, 1),
    dt.datetime(2012, 7, 1),
    dt.datetime(2015, 7, 1),
    dt.datetime(2017, 1, 1),
)
# Famous rollovers, as UTC instants: the Unix epoch, the millennium (also the
# instant that examples shrink towards), and the first moment beyond a signed
# 32-bit Unix timestamp.
_ROLLOVERS = (
    dt.datetime(1970, 1, 1),
    dt.datetime(2000, 1, 1),
    dt.datetime(2038, 1, 19, 3, 14, 8),
)


def _as_naive_datetime(value):
    """Bounds may be datetime subclasses such as ``pandas.Timestamp``, whose
    arithmetic can overflow its narrower representable range, and whose type
    must not leak into one side of a draw_capped_multipart window."""
    return dt.datetime(
        value.year,
        value.month,
        value.day,
        value.hour,
        value.minute,
        value.second,
        value.microsecond,
    )


def _tz_state(instant, tz):
    aware = instant.replace(tzinfo=dt.timezone.utc).astimezone(tz)
    return (aware.utcoffset(), aware.dst(), aware.tzname())


def _probe_transitions(tz, lo, hi):
    """Naive UTC instants in (lo, hi] at which ``tz`` first reports a changed
    (utcoffset, dst, tzname), found by scanning at _PROBE_STEP resolution and
    bisecting each change down to the second - the granularity of tzdata,
    though a tzinfo transitioning mid-second would be found within one.

    Because we resume scanning from each boundary we find, several
    transitions within a single step are all found; the only way to hide one
    is a pair of transitions less than _PROBE_STEP apart which revert to the
    exact prior state.  The closest real pair of transitions is just under
    seven days apart, comfortably above our six-day step, so in practice we
    find every transition of every zone (verified against the compiled
    transition lists in tzdata, via pytz, over the whole scan range).
    """
    transitions = []
    at, state = lo, _tz_state(lo, tz)
    while at < hi:
        try:
            probe = min(at + _PROBE_STEP, hi)
        except OverflowError:  # within _PROBE_STEP of datetime.max
            probe = hi
        probed = _tz_state(probe, tz)
        if probed == state:
            at, state = probe, probed
            continue
        low, high = at, probe
        while high - low > _SECOND:
            # Snap to whole seconds so that ``high`` converges to the exact
            # transition instant rather than up to a second beyond it.
            mid = (low + (high - low) / 2).replace(microsecond=0)
            if mid <= low:  # a sub-second window straddling a whole second
                mid = low + (high - low) / 2
            if _tz_state(mid, tz) == state:
                low = mid
            else:
                high = mid
        transitions.append(high)
        at, state = high, _tz_state(high, tz)
    return tuple(transitions)


@cache
def _transitions(tz):
    """All transitions of ``tz`` within [_SCAN_LO, _SCAN_HI], probed once per
    zone - a few tens of milliseconds each, for the zones actually drawn."""
    return _probe_transitions(tz, _SCAN_LO, _SCAN_HI)


@lru_cache(maxsize=256)
def _interesting_instants(tz, lo, hi):
    """The interesting instants for ``tz`` within the window of UTC instants
    [lo, hi], as a sorted tuple of naive datetimes, plus the index to shrink
    towards (the instant nearest year 2000).  Returns ``((), 0)`` if there
    are none, or if the tzinfo misbehaves when probed - inside this cached
    function, so that the structure of tricky draws can never vary between
    otherwise-identical calls.
    """
    try:
        if tz is None:
            transitions = ()
        elif lo > _SCAN_HI or hi < _SCAN_LO:
            # The window is wholly outside the usual scan range: probe a few
            # years directly, enough to cover any recurring annual rule.
            try:
                cap = lo + _FALLBACK_SCAN
            except OverflowError:  # within a few years of datetime.max
                cap = hi
            transitions = _probe_transitions(tz, lo, min(hi, cap))
        else:
            transitions = _transitions(tz)
    except Exception:
        return (), 0
    instants = tuple(
        t for t in sorted(transitions + _LEAP_SECONDS + _ROLLOVERS) if lo <= t <= hi
    )
    if not instants:
        return (), 0
    arbitrary = dt.datetime(2000, 1, 1)
    nearest = min(range(len(instants)), key=lambda i: abs(instants[i] - arbitrary))
    return instants, nearest


class _UnrepresentableBound(Exception):
    """No wall time in the timezone lies within the strategy's bounds."""


class DatetimeStrategy(SearchStrategy):
    def __init__(self, min_value, max_value, timezones_strat, allow_imaginary):
        super().__init__()
        assert isinstance(timezones_strat, SearchStrategy)
        assert isinstance(allow_imaginary, bool)
        self.aware = (min_value is not None and min_value.tzinfo is not None) or (
            max_value is not None and max_value.tzinfo is not None
        )
        if self.aware:
            for value in (min_value, max_value):
                assert value is None or (
                    isinstance(value, dt.datetime) and value.tzinfo is not None
                )
            # The instants bounding this strategy, as _instant() sort keys.
            # UTC offsets are less than a day, so a None bound is replaced by
            # a key which lies outside the representable range.
            self.min_instant = (
                dt.timedelta(days=-2) if min_value is None else _instant(min_value)
            )
            self.max_instant = (
                dt.datetime.max - dt.datetime.min + dt.timedelta(days=2)
                if max_value is None
                else _instant(max_value)
            )
            assert self.min_instant <= self.max_instant
        else:
            for value in (min_value, max_value):
                assert isinstance(value, dt.datetime)
                assert value.tzinfo is None
            assert min_value <= max_value
        self.min_value = min_value
        self.max_value = max_value
        self.tz_strat = timezones_strat
        self.allow_imaginary = allow_imaginary
        # The window of UTC instants (as naive datetimes) within which
        # draw_tricky_datetime looks for interesting instants.
        if self.aware:
            zero, whole = dt.timedelta(0), dt.datetime.max - dt.datetime.min
            lo = dt.datetime.min + min(max(self.min_instant, zero), whole)
            hi = dt.datetime.min + min(max(self.max_instant, zero), whole)
        else:
            slop = dt.timedelta(days=1)  # room for any UTC offset
            lo = max(dt.datetime.min + slop, _as_naive_datetime(min_value)) - slop
            hi = min(dt.datetime.max - slop, _as_naive_datetime(max_value)) + slop
        self.instant_window = (lo, hi)
        self.tricky_possible = any(
            lo <= t <= hi for t in _LEAP_SECONDS + _ROLLOVERS
        ) or (_timezones_kind(self.tz_strat) != "none")

    def do_draw(self, data):
        # We start by drawing a timezone, and then - with some probability -
        # target a "tricky" value near a timezone transition, leap second, or
        # famous rollover; see issue #69.
        tz = data.draw(self.tz_strat)
        if self.aware and not isinstance(tz, dt.tzinfo):
            raise InvalidArgument(
                f"Drew {tz!r} from the timezones strategy {self.tz_strat!r}, "
                "but with aware min_value/max_value bounds the timezones "
                "strategy must only generate tzinfo objects (not None)"
            )
        if self.tricky_possible and data.draw_boolean(_TRICKY_P):
            result = self.draw_tricky_datetime(data, tz)
        elif self.aware:
            result = self.draw_aware_datetime(data, tz)
        else:
            result = self.draw_naive_datetime_and_combine(data, tz)

        # If we happened to end up with a disallowed imaginary time, reject it.
        if (not self.allow_imaginary) and datetime_does_not_exist(result):
            data.mark_invalid(f"{result} does not exist (usually a DST transition)")
        return result

    def draw_tricky_datetime(self, data, tz):
        """Draw a wall time from a narrow window around one of the drawn
        timezone's interesting instants, clamped to the strategy's bounds so
        that the result satisfies them by construction.  If there is nothing
        tricky to aim for, fall back to an ordinary, unbiased draw."""
        try:
            instants, nearest = _interesting_instants(tz, *self.instant_window)
        except TypeError:  # an unhashable tzinfo, which raises on every call
            instants, nearest = (), 0
        if self.aware:
            try:
                window = self._wall_clock_window(tz)
            except _UnrepresentableBound:
                window = None
            if window is None:  # draw_aware_datetime uses the UTC frame here
                instants = ()
        else:
            window = (self.min_value, self.max_value)
        if not instants:
            if self.aware:
                return self.draw_aware_datetime(data, tz)
            return self.draw_naive_datetime_and_combine(data, tz)
        instant = instants[
            data.draw_integer(0, len(instants) - 1, shrink_towards=nearest)
        ]
        width = _TRICKY_WIDTHS[data.draw_integer(0, len(_TRICKY_WIDTHS) - 1)]
        if tz is not None:
            # This cannot overflow: transitions were converted to tz when we
            # probed for them, and the fixed instants are all C20-C21.
            instant = (
                instant.replace(tzinfo=dt.timezone.utc)
                .astimezone(tz)
                .replace(tzinfo=None)
            )
        lo, hi = (_as_naive_datetime(b) for b in window)
        center = min(max(instant, lo), hi)
        low = center - width if center - lo >= width else lo
        high = center + width if hi - center >= width else hi
        result = draw_capped_multipart(data, low, high)
        value = replace_tzinfo(dt.datetime(**result), timezone=tz)
        if self.aware and not self.in_bounds(value):
            # An ambiguous wall time next to a bound, with the out-of-bounds
            # fold - just as in draw_aware_datetime.
            data.mark_invalid(f"{value!r} is outside the bounds")
        return value

    def in_bounds(self, value):
        return self.min_instant <= _instant(value) <= self.max_instant

    def draw_aware_datetime(self, data, tz):
        try:
            window = self._wall_clock_window(tz)
        except _UnrepresentableBound as err:
            data.mark_invalid(str(err))
        if window is None:
            # A large fraction of the wall times between bounds inside or close
            # to a DST fold would risk rejection below - and bounds inside the
            # same fold may even be in inverted wall-clock order, like
            # 01:59 EDT < 01:01 EST - so we recurse to draw in UTC, where wall
            # times are unambiguous and ordered, and convert.  This is the
            # standard draw with the standard shrink order, except that
            # simplicity is judged on the UTC wall time rather than the local.
            value = self.draw_aware_datetime(data, dt.timezone.utc)
            try:
                return value.astimezone(tz)
            except OverflowError:
                data.mark_invalid(f"{value!r} is not representable in {tz!r}")
        result = draw_capped_multipart(data, *window)
        value = replace_tzinfo(dt.datetime(**result), timezone=tz)
        if not self.in_bounds(value):
            # An ambiguous wall time next to a bound, with the out-of-bounds fold.
            data.mark_invalid(f"{value!r} is outside the bounds")
        return value

    def _wall_clock_window(self, tz):
        """The naive (min, max) wall-clock bounds for drawing in ``tz``, or
        None to draw in UTC and convert.  A pure function of (bounds, tz),
        shared by generation and inversion; raises _UnrepresentableBound when
        no wall time in ``tz`` lies within the bounds."""

        def wall_clock(bound, extreme):
            if bound is None:
                return extreme
            try:
                return bound.astimezone(tz).replace(tzinfo=None)
            except OverflowError:
                # UTC offsets are less than a day, so an overflowing bound
                # must be within a day of datetime.min/max, converting to a
                # moment beyond them.  If every wall time representable in tz
                # is on the in-bounds side, the bound is simply vacuous here;
                # otherwise nothing in tz is in bounds.
                near_min = bound.replace(tzinfo=None) - dt.datetime.min < dt.timedelta(
                    days=2
                )
                if near_min == (extreme is dt.datetime.min):
                    return extreme
                raise _UnrepresentableBound(
                    f"{bound!r} is not representable in {tz!r}"
                ) from None

        min_local = wall_clock(self.min_value, dt.datetime.min)
        max_local = wall_clock(self.max_value, dt.datetime.max)
        if min_local > max_local or (
            max_local - min_local <= dt.timedelta(days=1)
            and (_ambiguous(min_local, tz) or _ambiguous(max_local, tz))
        ):
            return None
        return min_local, max_local

    def draw_naive_datetime_and_combine(self, data, tz):
        result = draw_capped_multipart(data, self.min_value, self.max_value)
        try:
            return replace_tzinfo(dt.datetime(**result), timezone=tz)
        except (ValueError, OverflowError):
            data.mark_invalid(
                f"Failed to draw a datetime between {self.min_value!r} and "
                f"{self.max_value!r} with timezone from {self.tz_strat!r}."
            )

    def _invert(self, value: Any) -> tuple[ChoiceT, ...]:
        # do_draw draws the tricky-path selector after the timezone, when one
        # is drawn at all; we always re-encode via the ordinary path, which
        # can produce any value of the strategy.
        selector = (False,) if self.tricky_possible else ()
        if self.aware:
            if type(value) is not dt.datetime or value.tzinfo is None:
                raise CannotInvert(f"{value!r} is not an aware datetime")
            try:
                in_bounds = self.in_bounds(value)
                imaginary = datetime_does_not_exist(value)
            except Exception:
                raise CannotInvert(
                    f"could not locate {value!r} relative to {self!r}"
                ) from None
            if not in_bounds:
                raise CannotInvert(f"{value!r} outside the instant bounds of {self!r}")
            if imaginary and not self.allow_imaginary:
                raise CannotInvert(
                    f"{value!r} is an imaginary datetime, but allow_imaginary=False"
                )
            return (
                *self.tz_strat._invert(value.tzinfo),
                *selector,
                *self._invert_aware_fields(value, value.tzinfo, imaginary=imaginary),
            )
        if type(value) is not dt.datetime:
            raise CannotInvert(f"{value!r} is not a datetime")
        naive = value.replace(tzinfo=None)
        if not (self.min_value <= naive <= self.max_value):
            raise CannotInvert(
                f"{value!r} outside [{self.min_value!r}, {self.max_value!r}]"
            )
        if not self.allow_imaginary and datetime_does_not_exist(value):
            raise CannotInvert(
                f"{value!r} is an imaginary datetime, but allow_imaginary=False"
            )
        # do_draw draws the timezone first, then the naive parts (with fold
        # drawn last, since it is ignored in datetime comparisons).
        return (
            *self.tz_strat._invert(value.tzinfo),
            *selector,
            value.year,
            value.month,
            value.day,
            value.hour,
            value.minute,
            value.second,
            value.microsecond,
            value.fold,
        )

    def _invert_aware_fields(self, value, tz, *, imaginary):
        # The multipart fields draw_aware_datetime would consume to produce
        # ``value``, expressed in the frame it would draw in for ``tz``.
        try:
            window = self._wall_clock_window(tz)
        except _UnrepresentableBound as err:
            raise CannotInvert(str(err)) from None
        if window is None:
            # do_draw would draw in UTC and convert; converting an imaginary
            # wall time to UTC and back does not round-trip, so be conservative.
            if imaginary:
                raise CannotInvert(
                    f"the UTC drawing frame cannot reproduce imaginary {value!r}"
                )
            try:
                utc_value = value.astimezone(dt.timezone.utc)
            except OverflowError:
                raise CannotInvert(f"{value!r} is not representable in UTC") from None
            return self._invert_aware_fields(
                utc_value, dt.timezone.utc, imaginary=False
            )
        min_local, max_local = window
        naive = value.replace(tzinfo=None)
        if not (min_local <= naive <= max_local):
            raise CannotInvert(
                f"{value!r} is outside the wall-clock window of {self!r} in {tz!r}"
            )
        return (
            naive.year,
            naive.month,
            naive.day,
            naive.hour,
            naive.minute,
            naive.second,
            naive.microsecond,
            value.fold,
        )

    def filter(self, condition):
        if (parsed := _comparator_bound(condition)) is not None and isinstance(
            arg := parsed[1], dt.datetime
        ):
            func = parsed[0]
            try:
                bound_aware = arg.utcoffset() is not None
            except Exception:
                # A tzinfo whose utcoffset() raises; comparing against this
                # bound will raise the same error at draw time.
                return super().filter(condition)
            if not bound_aware:
                # The bound compares as naive (either no tzinfo, or a tzinfo
                # without a UTC offset), so we can only rewrite it into the
                # naive wall-clock bounds if it really is naive and every
                # generated value is too.
                if (
                    arg.tzinfo is None
                    and not self.aware
                    and _timezones_kind(self.tz_strat) == "none"
                ):
                    bounds = _narrowed_bounds(
                        func, arg, self.min_value, self.max_value, _shift_datetime
                    )
                    if bounds is None:
                        return nothing()
                    if bounds == (self.min_value, self.max_value):
                        return self
                    return datetimes(
                        *bounds,
                        timezones=self.tz_strat,
                        allow_imaginary=self.allow_imaginary,
                    )
            else:
                # An aware bound constrains the instant of generated values,
                # so we narrow our aware bounds to the closed interval of
                # satisfying instants - retaining strict predicates below,
                # which then reject at most the boundary instant per timezone.
                # We compare bounds by their _instant() key, since comparison
                # of datetimes which share a tzinfo would fall back to
                # wall-clock order, ignoring the fold.
                if self.aware:
                    min_value, max_value = self.min_value, self.max_value
                elif (self.min_value, self.max_value) == (
                    dt.datetime.min,
                    dt.datetime.max,
                ) and _timezones_kind(self.tz_strat) != "none":
                    # An unbounded naive-mode strategy whose values are all
                    # aware: promote to aware mode, bounded by the filter.
                    min_value = max_value = None
                else:
                    return super().filter(condition)
                key = _instant(arg)
                if func in (op.lt, op.le, op.eq) and (
                    min_value is None or _instant(min_value) < key
                ):
                    min_value = arg
                if func in (op.gt, op.ge, op.eq) and (
                    max_value is None or key < _instant(max_value)
                ):
                    max_value = arg
                if min_value is not None and max_value is not None:
                    lo, hi = _instant(min_value), _instant(max_value)
                    if hi < lo or (func in (op.lt, op.gt) and lo == hi == key):
                        # Only aware-mode strategies can reach this, and they
                        # generate only aware values (or raise for a bad
                        # timezones strategy), so this is provably empty.
                        return nothing()
                if min_value is self.min_value and max_value is self.max_value:
                    result = self
                else:
                    result = DatetimeStrategy(
                        min_value, max_value, self.tz_strat, self.allow_imaginary
                    )
                if func in (op.lt, op.gt):
                    return FilteredStrategy(result, (condition,))
                return result
        return super().filter(condition)


@overload
def datetimes(
    min_value: NaiveDatetime | None = None,
    max_value: NaiveDatetime | None = None,
    *,
    timezones: SearchStrategy[None] | None = None,
) -> SearchStrategy[NaiveDatetime]: ...


@overload
def datetimes(
    min_value: dt.datetime | None = None,
    max_value: dt.datetime | None = None,
    *,
    timezones: SearchStrategy[dt.tzinfo],
    allow_imaginary: bool = True,
) -> SearchStrategy[AwareDatetime]: ...


@overload
def datetimes(
    min_value: None = None,
    max_value: None = None,
    *,
    timezones: SearchStrategy[dt.tzinfo | None],
    allow_imaginary: bool = True,
) -> SearchStrategy[dt.datetime]: ...


@defines_strategy(force_reusable_values=True)
def datetimes(
    min_value: dt.datetime | None = None,
    max_value: dt.datetime | None = None,
    *,
    timezones: SearchStrategy[dt.tzinfo | None] | None = None,
    allow_imaginary: bool = True,
) -> SearchStrategy[dt.datetime]:
    """datetimes(min_value=None, max_value=None, *, timezones=None, allow_imaginary=True)

    A strategy for generating datetimes, which may be timezone-aware.

    If ``min_value`` and ``max_value`` are naive datetimes, or omitted, this
    strategy works by drawing a naive datetime between them - defaulting to
    ``datetime.min`` and ``datetime.max`` respectively - and then attaching
    a timezone drawn from ``timezones``, which defaults to
    :func:`~hypothesis.strategies.none`.

    If instead both bounds are timezone-aware, they are treated as moments in
    time, and ``timezones`` defaults to :func:`~hypothesis.strategies.timezones`.
    Each generated datetime is aware, in a timezone drawn from ``timezones`` -
    which must not generate ``None`` - and lies between the two moments.
    Passing one aware and one naive bound is an error.

    ``timezones`` must be a strategy that generates either ``None``, for naive
    datetimes, or :class:`~python:datetime.tzinfo` objects for 'aware' datetimes.
    You can construct your own, though we recommend using one of these built-in
    strategies:

    * with the standard library: :func:`hypothesis.strategies.timezones`;
    * with :pypi:`dateutil <python-dateutil>`:
      :func:`hypothesis.extra.dateutil.timezones`; or
    * with :pypi:`pytz`: :func:`hypothesis.extra.pytz.timezones`.

    You may pass ``allow_imaginary=False`` to filter out "imaginary" datetimes
    which did not (or will not) occur due to daylight savings, leap seconds,
    timezone and calendar adjustments, etc.  Imaginary datetimes are allowed
    by default, because malformed timestamps are a common source of bugs.

    Because times near a change to the UTC offset are also a common source of
    bugs, this strategy deliberately generates values on or near the drawn
    timezone's daylight-saving and other offset transitions - including
    imaginary wall times, and ambiguous ones with each value of ``fold`` -
    as well as times adjacent to leap seconds and to famous rollovers such as
    the millennium and the end of the signed 32-bit Unix epoch.

    .. note::

        Arithmetic and comparisons on timezone-aware datetimes can be very
        surprising around daylight-savings changes.  See `this CPython issue
        <https://github.com/python/cpython/issues/116035>`__ for details
        and discussion.

    Examples from this strategy shrink towards midnight on January 1st 2000,
    local time.
    """
    check_type(bool, allow_imaginary, "allow_imaginary")
    if min_value is not None:
        check_type(dt.datetime, min_value, "min_value")
    if max_value is not None:
        check_type(dt.datetime, max_value, "max_value")
    if timezones is not None and not isinstance(timezones, SearchStrategy):
        raise InvalidArgument(
            f"{timezones=} must be a SearchStrategy that can "
            "provide tzinfo for datetimes (either None or dt.tzinfo objects)"
        )
    if (min_value is None or min_value.tzinfo is None) and (
        max_value is None or max_value.tzinfo is None
    ):
        min_value = dt.datetime.min if min_value is None else min_value
        max_value = dt.datetime.max if max_value is None else max_value
        if timezones is None:
            timezones = none()
        check_valid_interval(min_value, max_value, "min_value", "max_value")
    else:
        # Aware bounds describe moments in time; we check both are aware here,
        # and then at draw time convert them to the drawn timezone and proceed
        # as in the naive case.
        for name, value in [("min_value", min_value), ("max_value", max_value)]:
            if value is not None and value.tzinfo is None:
                raise InvalidArgument(
                    f"{name}={value!r} is naive, but the other bound is "
                    "timezone-aware; the bounds must be both naive or both aware"
                )
        if timezones is None:
            timezones = _timezones()
        # Compare explicitly as moments in time: comparison of datetimes which
        # share a tzinfo falls back to wall-clock order, ignoring the fold.
        if (
            min_value is not None
            and max_value is not None
            and _instant(max_value) < _instant(min_value)
        ):
            raise InvalidArgument(
                f"Cannot have {max_value=} < {min_value=}, comparing as "
                "moments in time"
            )
    return DatetimeStrategy(min_value, max_value, timezones, allow_imaginary)


_ARBITRARY_DATE = dt.date(2000, 1, 1)


def _shift_time(value, steps):
    # dt.time supports no arithmetic, so we go via a datetime on a fixed day
    # and treat crossing midnight as overflowing the representable range.
    shifted = dt.datetime.combine(_ARBITRARY_DATE, value) + steps * _MICROSECOND
    if shifted.date() != _ARBITRARY_DATE:
        raise OverflowError
    return shifted.time()


class TimeStrategy(SearchStrategy):
    def __init__(self, min_value, max_value, timezones_strat):
        super().__init__()
        self.min_value = min_value
        self.max_value = max_value
        self.tz_strat = timezones_strat

    def do_draw(self, data):
        result = draw_capped_multipart(data, self.min_value, self.max_value, TIMENAMES)
        tz = data.draw(self.tz_strat)
        return dt.time(**result, tzinfo=tz)

    def _invert(self, value: Any) -> tuple[ChoiceT, ...]:
        if type(value) is not dt.time:
            raise CannotInvert(f"{value!r} is not a time")
        naive = value.replace(tzinfo=None)
        if not (self.min_value <= naive <= self.max_value):
            raise CannotInvert(
                f"{value!r} outside [{self.min_value!r}, {self.max_value!r}]"
            )
        # unlike DatetimeStrategy, do_draw draws the naive parts first - with
        # fold at the end, via draw_capped_multipart - and the timezone last.
        return (
            value.hour,
            value.minute,
            value.second,
            value.microsecond,
            value.fold,
            *self.tz_strat._invert(value.tzinfo),
        )

    def filter(self, condition):
        # We only rewrite naive times: ordering aware times works in terms of
        # utcoffset(), which is None for e.g. ZoneInfo tzinfos on a time - so
        # such values compare as naive anyway, and rewriting fixed-offset aware
        # times isn't worth the extra complexity.
        if (
            (parsed := _comparator_bound(condition)) is not None
            and isinstance(arg := parsed[1], dt.time)
            and arg.tzinfo is None
            and _timezones_kind(self.tz_strat) == "none"
        ):
            bounds = _narrowed_bounds(
                parsed[0], arg, self.min_value, self.max_value, _shift_time
            )
            if bounds is None:
                return nothing()
            if bounds == (self.min_value, self.max_value):
                return self
            return times(*bounds, timezones=self.tz_strat)
        return super().filter(condition)


@defines_strategy(force_reusable_values=True)
def times(
    min_value: dt.time = dt.time.min,
    max_value: dt.time = dt.time.max,
    *,
    timezones: SearchStrategy[dt.tzinfo | None] = none(),
) -> SearchStrategy[dt.time]:
    """times(min_value=datetime.time.min, max_value=datetime.time.max, *, timezones=none())

    A strategy for times between ``min_value`` and ``max_value``.

    The ``timezones`` argument is handled as for :py:func:`datetimes`.

    Examples from this strategy shrink towards midnight, with the timezone
    component shrinking as for the strategy that provided it.
    """
    check_type(dt.time, min_value, "min_value")
    check_type(dt.time, max_value, "max_value")
    if min_value.tzinfo is not None:
        raise InvalidArgument(f"{min_value=} must not have tzinfo")
    if max_value.tzinfo is not None:
        raise InvalidArgument(f"{max_value=} must not have tzinfo")
    check_valid_interval(min_value, max_value, "min_value", "max_value")
    return TimeStrategy(min_value, max_value, timezones)


def _shift_date(value, steps):
    return value + steps * dt.timedelta(days=1)


class DateStrategy(SearchStrategy):
    def __init__(self, min_value, max_value):
        super().__init__()
        assert isinstance(min_value, dt.date)
        assert isinstance(max_value, dt.date)
        assert min_value < max_value
        self.min_value = min_value
        self.max_value = max_value

    def do_draw(self, data):
        return dt.date(
            **draw_capped_multipart(data, self.min_value, self.max_value, DATENAMES)
        )

    def _invert(self, value: Any) -> tuple[ChoiceT, ...]:
        if type(value) is not dt.date:
            raise CannotInvert(f"{value!r} is not a date")
        if not (self.min_value <= value <= self.max_value):
            raise CannotInvert(
                f"{value!r} outside [{self.min_value!r}, {self.max_value!r}]"
            )
        return (value.year, value.month, value.day)

    def filter(self, condition):
        if (
            (parsed := _comparator_bound(condition)) is not None
            # datetime is a date subclass, but not comparable with dates
            and isinstance(arg := parsed[1], dt.date)
            and not isinstance(arg, dt.datetime)
        ):
            bounds = _narrowed_bounds(
                parsed[0], arg, self.min_value, self.max_value, _shift_date
            )
            if bounds is None:
                return nothing()
            if bounds == (self.min_value, self.max_value):
                return self
            return dates(*bounds)

        return super().filter(condition)


@defines_strategy(force_reusable_values=True)
def dates(
    min_value: dt.date = dt.date.min, max_value: dt.date = dt.date.max
) -> SearchStrategy[dt.date]:
    """dates(min_value=datetime.date.min, max_value=datetime.date.max)

    A strategy for dates between ``min_value`` and ``max_value``.

    Examples from this strategy shrink towards January 1st 2000.
    """
    check_type(dt.date, min_value, "min_value")
    check_type(dt.date, max_value, "max_value")
    # datetime is a subclass of date, so check_type() accepts it - but a datetime
    # bound is almost certainly a mistake, and breaks our drawing logic downstream.
    if isinstance(min_value, dt.datetime):
        raise InvalidArgument(f"{min_value=} is a datetime, but expected a date")
    if isinstance(max_value, dt.datetime):
        raise InvalidArgument(f"{max_value=} is a datetime, but expected a date")
    check_valid_interval(min_value, max_value, "min_value", "max_value")
    if min_value == max_value:
        return just(min_value)
    return DateStrategy(min_value, max_value)


class TimedeltaStrategy(SearchStrategy):
    def __init__(self, min_value, max_value):
        super().__init__()
        assert isinstance(min_value, dt.timedelta)
        assert isinstance(max_value, dt.timedelta)
        assert min_value < max_value
        self.min_value = min_value
        self.max_value = max_value

    def do_draw(self, data):
        result = {}
        low_bound = True
        high_bound = True
        for name in ("days", "seconds", "microseconds"):
            low = getattr(self.min_value if low_bound else dt.timedelta.min, name)
            high = getattr(self.max_value if high_bound else dt.timedelta.max, name)
            val = data.draw_integer(low, high)
            result[name] = val
            low_bound = low_bound and val == low
            high_bound = high_bound and val == high
        return dt.timedelta(**result)

    def _invert(self, value: Any) -> tuple[ChoiceT, ...]:
        if type(value) is not dt.timedelta:
            raise CannotInvert(f"{value!r} is not a timedelta")
        if not (self.min_value <= value <= self.max_value):
            raise CannotInvert(
                f"{value!r} outside [{self.min_value!r}, {self.max_value!r}]"
            )
        return (value.days, value.seconds, value.microseconds)


@defines_strategy(force_reusable_values=True)
def timedeltas(
    min_value: dt.timedelta = dt.timedelta.min,
    max_value: dt.timedelta = dt.timedelta.max,
) -> SearchStrategy[dt.timedelta]:
    """timedeltas(min_value=datetime.timedelta.min, max_value=datetime.timedelta.max)

    A strategy for timedeltas between ``min_value`` and ``max_value``.

    Examples from this strategy shrink towards zero.
    """
    check_type(dt.timedelta, min_value, "min_value")
    check_type(dt.timedelta, max_value, "max_value")
    check_valid_interval(min_value, max_value, "min_value", "max_value")
    if min_value == max_value:
        return just(min_value)
    return TimedeltaStrategy(min_value=min_value, max_value=max_value)


@cache
def _valid_key_cacheable(tzpath, key):
    assert isinstance(tzpath, tuple)  # zoneinfo changed, better update this function!
    for root in tzpath:
        if Path(root).joinpath(key).exists():  # pragma: no branch
            # No branch because most systems only have one TZPATH component.
            return True
    else:
        # Taken for names which are known to zoneinfo but not present on the
        # filesystem, e.g. with the tzdata package installed.
        *package_loc, resource_name = key.split("/")
        package = "tzdata.zoneinfo." + ".".join(package_loc)
        try:
            return (resources.files(package) / resource_name).exists()
        except ModuleNotFoundError:
            return False


def _timezone_key_strategies(*, allow_prefix):
    """SampledFromStrategy branches for IANA keys: plain keys first, then one
    branch per allowed prefix, with the prefix applied as a sampled_from
    transformation. one_of's branch selector is therefore the prefix choice,
    which shrinks towards - and can be re-encoded as - an unprefixed key."""
    with warnings.catch_warnings():
        try:
            warnings.simplefilter("ignore", EncodingWarning)
        except NameError:  # pragma: no cover
            pass
        # On Python 3.12 (and others?), `available_timezones()` opens files
        # without specifying an encoding - which our selftests make an error.
        available_timezones = ("UTC", *sorted(zoneinfo.available_timezones()))

    # TODO: filter out alias and deprecated names if disallowed

    def valid_key(key):
        return key == "UTC" or _valid_key_cacheable(zoneinfo.TZPATH, key)

    # TODO: work out how to place a higher priority on "weird" timezones
    # For details see https://github.com/HypothesisWorks/hypothesis/issues/2414
    plain = [key for key in available_timezones if valid_key(key)]
    branches = [sampled_from(plain)]
    if allow_prefix:
        for prefix in ("posix", "right"):
            keys = [key for key in plain if valid_key(f"{prefix}/{key}")]
            if keys:
                branches.append(sampled_from(keys).map(f"{prefix}/{{}}".format))
    return branches


@defines_strategy(force_reusable_values=True)
def timezone_keys(
    *,
    # allow_alias: bool = True,
    # allow_deprecated: bool = True,
    allow_prefix: bool = True,
) -> SearchStrategy[str]:
    """A strategy for :wikipedia:`IANA timezone names <List_of_tz_database_time_zones>`.

    As well as timezone names like ``"UTC"``, ``"Australia/Sydney"``, or
    ``"America/New_York"``, this strategy can generate:

    - Aliases such as ``"Antarctica/McMurdo"``, which links to ``"Pacific/Auckland"``.
    - Deprecated names such as ``"Antarctica/South_Pole"``, which *also* links to
      ``"Pacific/Auckland"``.  Note that most but
      not all deprecated timezone names are also aliases.
    - Timezone names with the ``"posix/"`` or ``"right/"`` prefixes, unless
      ``allow_prefix=False``.

    These strings are provided separately from Tzinfo objects - such as ZoneInfo
    instances from the timezones() strategy - to facilitate testing of timezone
    logic without needing workarounds to access non-canonical names.

    .. note::

        `The tzdata package is required on Windows
        <https://docs.python.org/3/library/zoneinfo.html#data-sources>`__.
        ``pip install hypothesis[zoneinfo]`` installs it, if and only if needed.

    On Windows, you may need to access IANA timezone data via the :pypi:`tzdata`
    package.  For non-IANA timezones, such as Windows-native names or GNU TZ
    strings, we recommend using :func:`~hypothesis.strategies.sampled_from` with
    the :pypi:`dateutil <python-dateutil>` package, e.g.
    :meth:`dateutil:dateutil.tz.tzwin.list`.
    """
    # check_type(bool, allow_alias, "allow_alias")
    # check_type(bool, allow_deprecated, "allow_deprecated")
    check_type(bool, allow_prefix, "allow_prefix")
    return one_of(_timezone_key_strategies(allow_prefix=allow_prefix))


@defines_strategy(force_reusable_values=True)
def timezones(*, no_cache: bool = False) -> SearchStrategy["zoneinfo.ZoneInfo"]:
    """A strategy for :class:`python:zoneinfo.ZoneInfo` objects.

    If ``no_cache=True``, the generated instances are constructed using
    :meth:`ZoneInfo.no_cache <python:zoneinfo.ZoneInfo.no_cache>` instead
    of the usual constructor.  This may change the semantics of your datetimes
    in surprising ways, so only use it if you know that you need to!

    .. note::

        `The tzdata package is required on Windows
        <https://docs.python.org/3/library/zoneinfo.html#data-sources>`__.
        ``pip install hypothesis[zoneinfo]`` installs it, if and only if needed.
    """
    check_type(bool, no_cache, "no_cache")
    ctor = zoneinfo.ZoneInfo.no_cache if no_cache else zoneinfo.ZoneInfo
    # Mapping each sampled_from branch folds ctor into its transformations,
    # keeping the whole strategy re-encodable (unlike mapping the one_of).
    return one_of(
        [keys.map(ctor) for keys in _timezone_key_strategies(allow_prefix=True)]
    )


# In datetimes() above, the ``timezones`` argument shadows this module's
# timezones() strategy, so we refer to it by this alias instead.
_timezones = timezones
