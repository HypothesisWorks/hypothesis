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

import datetime as dt
from calendar import monthrange
from typing import Optional

from hypothesis.errors import InvalidArgument
from hypothesis.internal.conjecture import utils
from hypothesis.internal.validation import check_type, check_valid_interval
from hypothesis.strategies._internal.core import (
    defines_strategy_with_reusable_values,
    deprecated_posargs,
    just,
    none,
)
from hypothesis.strategies._internal.strategies import SearchStrategy

DATENAMES = ("year", "month", "day")
TIMENAMES = ("hour", "minute", "second", "microsecond")


def is_pytz_timezone(tz):
    if not isinstance(tz, dt.tzinfo):
        return False
    module = type(tz).__module__
    return module == "pytz" or module.startswith("pytz.")


def draw_capped_multipart(data, min_value, max_value):
    assert isinstance(min_value, (dt.date, dt.time, dt.datetime))
    assert type(min_value) == type(max_value)
    assert min_value <= max_value
    result = {}
    cap_low, cap_high = True, True
    duration_names_by_type = {
        dt.date: DATENAMES,
        dt.time: TIMENAMES,
        dt.datetime: DATENAMES + TIMENAMES,
    }
    for name in duration_names_by_type[type(min_value)]:
        low = getattr(min_value if cap_low else dt.datetime.min, name)
        high = getattr(max_value if cap_high else dt.datetime.max, name)
        if name == "day" and not cap_high:
            _, high = monthrange(**result)
        if name == "year":
            val = utils.integer_range(data, low, high, 2000)
        else:
            val = utils.integer_range(data, low, high)
        result[name] = val
        cap_low = cap_low and val == low
        cap_high = cap_high and val == high
    return result


class DatetimeStrategy(SearchStrategy):
    def __init__(self, min_value, max_value, timezones_strat):
        assert isinstance(min_value, dt.datetime)
        assert isinstance(max_value, dt.datetime)
        assert min_value.tzinfo is None
        assert max_value.tzinfo is None
        assert min_value <= max_value
        assert isinstance(timezones_strat, SearchStrategy)
        self.min_value = min_value
        self.max_value = max_value
        self.tz_strat = timezones_strat

    def do_draw(self, data):
        result = draw_capped_multipart(data, self.min_value, self.max_value)
        result = dt.datetime(**result)
        tz = data.draw(self.tz_strat)
        try:
            if is_pytz_timezone(tz):
                # Can't just construct; see http://pytz.sourceforge.net
                return tz.normalize(tz.localize(result))
            return result.replace(tzinfo=tz)
        except (ValueError, OverflowError):
            msg = "Failed to draw a datetime between %r and %r with timezone from %r."
            data.note_event(msg % (self.min_value, self.max_value, self.tz_strat))
            data.mark_invalid()


@defines_strategy_with_reusable_values
@deprecated_posargs
def datetimes(
    min_value: dt.datetime = dt.datetime.min,
    max_value: dt.datetime = dt.datetime.max,
    *,
    timezones: SearchStrategy[Optional[dt.tzinfo]] = none()
) -> SearchStrategy[dt.datetime]:
    """datetimes(min_value=datetime.datetime.min, max_value=datetime.datetime.max, *, timezones=none())

    A strategy for generating datetimes, which may be timezone-aware.

    This strategy works by drawing a naive datetime between ``min_value``
    and ``max_value``, which must both be naive (have no timezone).

    ``timezones`` must be a strategy that generates
    :class:`~python:datetime.tzinfo` objects (or None,
    which is valid for naive datetimes).  A value drawn from this strategy
    will be added to a naive datetime, and the resulting tz-aware datetime
    returned.

    .. note::
        tz-aware datetimes from this strategy may be ambiguous or non-existent
        due to daylight savings, leap seconds, timezone and calendar
        adjustments, etc.  This is intentional, as malformed timestamps are a
        common source of bugs.

    :py:func:`hypothesis.extra.pytz.timezones` requires the :pypi:`pytz`
    package, but provides all timezones in the Olsen database.
    :py:func:`hypothesis.extra.dateutil.timezones` requires the
    :pypi:`python-dateutil` package, and similarly provides all timezones
    there.  If you want to allow naive datetimes, combine strategies
    like ``none() | timezones()``.

    Alternatively, you can create a list of the timezones you wish to allow
    (e.g. from the standard library, :pypi:`dateutil <python-dateutil>`,
    or :pypi:`pytz`) and use :py:func:`sampled_from`.

    Examples from this strategy shrink towards midnight on January 1st 2000,
    local time.
    """
    # Why must bounds be naive?  In principle, we could also write a strategy
    # that took aware bounds, but the API and validation is much harder.
    # If you want to generate datetimes between two particular moments in
    # time I suggest (a) just filtering out-of-bounds values; (b) if bounds
    # are very close, draw a value and subtract its UTC offset, handling
    # overflows and nonexistent times; or (c) do something customised to
    # handle datetimes in e.g. a four-microsecond span which is not
    # representable in UTC.  Handling (d), all of the above, leads to a much
    # more complex API for all users and a useful feature for very few.
    check_type(dt.datetime, min_value, "min_value")
    check_type(dt.datetime, max_value, "max_value")
    if min_value.tzinfo is not None:
        raise InvalidArgument("min_value=%r must not have tzinfo" % (min_value,))
    if max_value.tzinfo is not None:
        raise InvalidArgument("max_value=%r must not have tzinfo" % (max_value,))
    check_valid_interval(min_value, max_value, "min_value", "max_value")
    if not isinstance(timezones, SearchStrategy):
        raise InvalidArgument(
            "timezones=%r must be a SearchStrategy that can provide tzinfo "
            "for datetimes (either None or dt.tzinfo objects)" % (timezones,)
        )
    return DatetimeStrategy(min_value, max_value, timezones)


@defines_strategy_with_reusable_values
@deprecated_posargs
def times(
    min_value: dt.time = dt.time.min,
    max_value: dt.time = dt.time.max,
    *,
    timezones: SearchStrategy[Optional[dt.tzinfo]] = none()
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
        raise InvalidArgument("min_value=%r must not have tzinfo" % min_value)
    if max_value.tzinfo is not None:
        raise InvalidArgument("max_value=%r must not have tzinfo" % max_value)
    check_valid_interval(min_value, max_value, "min_value", "max_value")
    day = dt.date(2000, 1, 1)
    return datetimes(
        min_value=dt.datetime.combine(day, min_value),
        max_value=dt.datetime.combine(day, max_value),
        timezones=timezones,
    ).map(lambda t: t.timetz())


class DateStrategy(SearchStrategy):
    def __init__(self, min_value, max_value):
        assert isinstance(min_value, dt.date)
        assert isinstance(max_value, dt.date)
        assert min_value < max_value
        self.min_value = min_value
        self.max_value = max_value

    def do_draw(self, data):
        return dt.date(**draw_capped_multipart(data, self.min_value, self.max_value))


@defines_strategy_with_reusable_values
def dates(
    min_value: dt.date = dt.date.min, max_value: dt.date = dt.date.max
) -> SearchStrategy[dt.date]:
    """dates(min_value=datetime.date.min, max_value=datetime.date.max)

    A strategy for dates between ``min_value`` and ``max_value``.

    Examples from this strategy shrink towards January 1st 2000.
    """
    check_type(dt.date, min_value, "min_value")
    check_type(dt.date, max_value, "max_value")
    check_valid_interval(min_value, max_value, "min_value", "max_value")
    if min_value == max_value:
        return just(min_value)
    return DateStrategy(min_value, max_value)


class TimedeltaStrategy(SearchStrategy):
    def __init__(self, min_value, max_value):
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
            val = utils.integer_range(data, low, high, 0)
            result[name] = val
            low_bound = low_bound and val == low
            high_bound = high_bound and val == high
        return dt.timedelta(**result)


@defines_strategy_with_reusable_values
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
