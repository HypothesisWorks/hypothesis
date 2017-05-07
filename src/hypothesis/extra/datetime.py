# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2017 David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
# CONTRIBUTING.rst for a full list of people who may hold copyright, and
# consult the git log if you need to determine who owns an individual
# contribution.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.
#
# END HEADER

"""This module provides strategies for objects from the ``datetime`` module.

It includes strategies for generating ``datetime``\s, ``date``\s, and
``time``\s, and depends on the ``pytz`` package, which is stable enough
that almost any version should be compatible.  We still suggest using a
recent version so that the tzinfo data is up to date!

.. testsetup:: *

    import datetime as dt
    import pytz
    from hypothesis.extra.datetime import *

"""

from __future__ import division, print_function, absolute_import

import datetime as dt

import pytz

import hypothesis.internal.conjecture.utils as cu
from hypothesis.errors import InvalidState, InvalidArgument
from hypothesis._settings import note_deprecation
from hypothesis.strategies import just, defines_strategy, \
    check_valid_interval
from hypothesis.searchstrategy.strategies import SearchStrategy

__all__ = ['datetimes', 'dates', 'times']


def is_representable(datetime, tz):
    try:
        tz.normalize(datetime.astimezone(tz))
        return True
    except OverflowError:
        return False


class DatetimeStrategy(SearchStrategy):

    def __init__(self, allow_naive, timezones,
                 min_datetime=None, max_datetime=None):
        # All validation should have been handled in constructor functions,
        # so we can simply assert the invariants here.  See `datetimes()`.
        assert timezones or allow_naive
        assert not (allow_naive and (min_datetime.tzinfo is not None))
        assert all(isinstance(tz, dt.tzinfo) for tz in timezones)
        assert (min_datetime.tzinfo is None) == (max_datetime.tzinfo is None)
        assert isinstance(min_datetime, dt.datetime)
        assert isinstance(max_datetime, dt.datetime)
        assert min_datetime <= max_datetime

        self.allow_naive = allow_naive
        self.timezones = tuple(timezones)
        self.min_dt = min_datetime
        self.max_dt = max_datetime

    @staticmethod
    def _draw_naive(data, min_dt, max_dt):
        # Draw a naive datetime between naive bounds
        assert min_dt <= max_dt
        while True:
            result = dict()
            constrained_low = True
            constrained_high = True
            for name in ('year', 'month', 'day',
                         'hour', 'minute', 'second', 'microsecond'):
                low = getattr(dt.datetime.min, name)
                high = getattr(dt.datetime.max, name)
                if constrained_low:
                    low = max(low, getattr(min_dt, name))
                if constrained_high:
                    high = min([high, getattr(max_dt, name)])
                if name == 'year':
                    val = cu.centered_integer_range(data, low, high, 2000)
                else:
                    val = cu.integer_range(data, low, high)
                result[name] = val
                constrained_low = constrained_low and val == low
                constrained_high = constrained_high and val == high
            try:
                return dt.datetime(tzinfo=min_dt.tzinfo, **result)
            except ValueError:
                # We tried to draw a non-existent time, e.g. Feb 31
                continue

    def do_draw(self, data):
        if self.min_dt.tzinfo == self.max_dt.tzinfo:
            # No need to pick a timezone; they're the same (or both naive)
            min_dt = self.min_dt
            max_dt = self.max_dt
        else:
            # Choose a timezone to work in on this draw
            if cu.boolean(data):
                min_dt = self.min_dt
                try:
                    max_dt = self.max_dt.astimezone(self.min_dt.tzinfo)
                except OverflowError:  # pragma: no cover  # pytest internals
                    max_dt = self.min_dt.tzinfo.localize(dt.datetime.max)
            else:
                max_dt = self.max_dt
                try:
                    min_dt = self.min_dt.astimezone(self.max_dt.tzinfo)
                except OverflowError:
                    min_dt = self.max_dt.tzinfo.localize(dt.datetime.min)

        result = self._draw_naive(data, min_dt, max_dt)
        if (not self.timezones) or (self.allow_naive and cu.boolean(data)):
            if self.min_dt.tzinfo is None:
                return result
        timezones = list(self.timezones)
        for _ in range(len(self.timezones)):
            to_tz = cu.choice(data, timezones)
            try:
                if self.min_dt.tzinfo is None:
                    return to_tz.normalize(to_tz.localize(result))
                else:
                    return to_tz.normalize(result.astimezone(to_tz))
            except OverflowError:
                timezones.remove(to_tz)
        raise InvalidState('Reached impossible state')  # pragma: no cover


@defines_strategy
def datetimes(allow_naive=None, timezones=None, min_year=None, max_year=None,
              min_datetime=None, max_datetime=None):
    """Return a strategy for generating datetimes.

    allow_naive=True will cause the values to sometimes be naive (to make
    all values naive, use ``timezones=[]``), which may not be combined with
    tz-aware bounds.  allow_naive=False will make all values tz-aware, which
    requires that at least one timezone be allowed.  allow_naive=None will
    detect the right thing to do, and default to False if either would be
    possible.

    timezones is the set of permissible timezones. If set to an empty
    collection only naive datetimes will be drawn. If set to None all
    available timezones will be used.  Note that aware bounds may have a
    timezone that is not in this list.

    There are two ways to set bounds on the values from this strategy:
    timezone-aware and naive.

    If two timezone-aware datetime objects are used as the bounds, all
    values drawn from the strategy will be timezone-aware.  The moment
    in time represented by a drawn value will be between the moments
    represented by the bounds.  Because values may be represented in
    any of the supplied timezones, a naive comparison may show that a value
    is out of bounds - for example, 10am in London is actually earlier than
    8am in New York.

    If two naive date or datetime objects are used as the bounds, values
    drawn from the strategy may or may not be timezone-aware.
    All values will lie between the bounds when their tzinfo is ignored.
    If a date object is used, time information will be added to allow the
    widest possible range of values.

    The min_year and max_year arguments are deprecated, but if given they
    allow the widest range of values possible in the same way as dates.

    For example:

    .. doctest::

      >>> datetimes().example()
      datetime.datetime(9227, 9, 27, 17, 33, 33, 847373, tzinfo=<...>)
      >>> datetimes().example()
      datetime.datetime(494, 7, 2, 7, 12, 30, 402123, tzinfo=<...>)

    As you can see, it produces years from quite a wide range. If you want to
    narrow it down you can ask for a more specific range of years:

    .. doctest::

      >>> datetimes(min_datetime=dt.date(9000, 1, 1)).example()
      datetime.datetime(9877, 9, 17, 19, 14, 49, 61323, tzinfo=<...>)
      >>> datetimes(min_datetime=dt.date(2001, 1, 1),
      ...           max_datetime=dt.date(2010, 12, 31)).example()
      datetime.datetime(2001, 1, 21, 15, 8, 59, 228556, tzinfo=<...>)

    You can also specify timezones:

    .. doctest::

      >>> pytz.all_timezones[:3]
      ['Africa/Abidjan', 'Africa/Accra', 'Africa/Addis_Ababa']
      >>> datetimes(timezones=pytz.all_timezones[:3]).example()
      ... # doctest: +NORMALIZE_WHITESPACE
      datetime.datetime(4872, 10, 1, 20, 18, 36, 872201,
                        tzinfo=<DstTzInfo 'Africa/Abidjan' ...>)
      >>> datetimes(timezones=pytz.all_timezones[:3]).example()
      ... # doctest: +NORMALIZE_WHITESPACE
      datetime.datetime(595, 4, 25, 10, 14, 53, 523410,
                        tzinfo=<DstTzInfo 'Africa/Accra' ...>)
      >>> datetimes(timezones=pytz.all_timezones[:3]).example()
      ... # doctest: +NORMALIZE_WHITESPACE
      datetime.datetime(5437, 3, 7, 4, 54, 39, 774165,
                        tzinfo=<DstTzInfo 'Africa/Abidjan' ...>)

    """
    # Handle and validate timezones, allow_naive arguments
    if timezones is None:
        timezones = list(pytz.all_timezones)
        timezones.remove(u'UTC')
        timezones.insert(0, u'UTC')
    timezones = [tz if isinstance(tz, dt.tzinfo) else pytz.timezone(tz)
                 for tz in timezones]
    if allow_naive is None:
        allow_naive = not timezones
    if not (allow_naive or timezones):
        raise InvalidArgument('Cannot create non-naive datetimes with '
                              'no timezones allowed')

    # Handle deprecation and conversion of min_year and max_year arguments
    if (min_year is not None) or (max_year is not None):
        if (min_datetime is not None) or (max_datetime is not None):
            raise InvalidArgument(
                'You cannot mix old-style (min_year/max_year) and new-style '
                '(min_datetime/max_datetime) arguments to the datetimes '
                'strategy.')
        msg = ('The %s argument is deprecated.  Please use %s_datetime '
               'with a datetime.datetime or datetime.date object instead.')
        if min_year is not None:
            note_deprecation(msg % ('min_year', 'min'))
            try:
                min_datetime = dt.datetime.min.replace(year=min_year)
            except ValueError:
                raise InvalidArgument(
                    'min_year=%r is out of range or invalid' % min_year)
        if max_year is not None:
            note_deprecation(msg % ('max_year', 'max'))
            try:
                max_datetime = dt.datetime.max.replace(year=max_year)
            except ValueError:
                raise InvalidArgument(
                    'max_year=%r is out of range or invalid' % max_year)
    del min_year
    del max_year

    # First, we need to convert from date to naive datetime objects
    if (min_datetime is not None) and isinstance(min_datetime, dt.date) \
            and not isinstance(min_datetime, dt.datetime):
        min_datetime = dt.datetime.min.replace(year=min_datetime.year,
                                               month=min_datetime.month,
                                               day=min_datetime.day)
    if (max_datetime is not None) and isinstance(max_datetime, dt.date) \
            and not isinstance(max_datetime, dt.datetime):
        max_datetime = dt.datetime.max.replace(year=max_datetime.year,
                                               month=max_datetime.month,
                                               day=max_datetime.day)

    # Unlike dates() below, we need to distinguish naive from aware bounds,
    # so we'll be stuck with this after the deprecation period too.
    if not isinstance(min_datetime, dt.datetime) and min_datetime is not None:
        raise InvalidArgument(
            'min_datetime must be a datetime.datetime object.')
    if not isinstance(max_datetime, dt.datetime) and max_datetime is not None:
        raise InvalidArgument(
            'max_datetime must be a datetime.datetime object.')
    if (min_datetime is not None) and (max_datetime is not None):
        if (min_datetime.tzinfo is None) != (max_datetime.tzinfo is None):
            raise InvalidArgument((
                'min_datetime=%r and max_datetime=%r must not mix naive '
                'and tz-aware values.  See the documentation for how each '
                'of these modes work.') % (min_datetime, max_datetime))
    elif min_datetime is not None:
        assert max_datetime is None
        if min_datetime.tzinfo is None:
            max_datetime = dt.datetime.max
        else:
            naive = dt.datetime.max - dt.timedelta(days=1)
            max_datetime = min([tz.normalize(tz.localize(naive))
                                for tz in timezones])
            max_datetime += dt.timedelta(days=1)
    elif max_datetime is not None:
        assert min_datetime is None
        if max_datetime.tzinfo is None:
            min_datetime = dt.datetime.min
        else:
            naive = dt.datetime.min + dt.timedelta(days=1)
            min_datetime = min([tz.normalize(tz.localize(naive))
                                for tz in timezones])
            min_datetime -= dt.timedelta(days=1)
    else:
        assert min_datetime is None
        assert max_datetime is None
        min_datetime = dt.datetime.min
        max_datetime = dt.datetime.max

    # Check that our bounds are of the correct type and ordered correctly
    check_valid_interval(min_datetime, max_datetime,
                         'min_datetime', 'max_datetime')

    # Check that allow_naive and timezones args will work with aware bounds
    if min_datetime.tzinfo is not None:
        if allow_naive:
            raise InvalidArgument(
                'Cannot create naive datetimes between tz-aware bounds as '
                'they are not comparable; do not set allow_naive=True.')
        if not timezones:
            raise InvalidArgument(
                'Cannot create naive datetimes between tz-aware bounds as '
                'they are not comparable; at least one timezone is required.')

    # The final step of validation is to ensure that every drawable datetime
    # can be represented in at least one of the provided timezones.
    # This is an expensive check, but it's check now or error later.
    if min_datetime.tzinfo is not None:
        msg = ('It is impossible to localise %s=%r in any of the given '
               'timezones, illegally reducing the range of values which may '
               'otherwise be drawn.')
        if not any(is_representable(min_datetime, tz) for tz in timezones):
            raise InvalidArgument(msg % ('min_datetime', min_datetime))
        if not any(is_representable(max_datetime, tz) for tz in timezones):
            raise InvalidArgument(msg % ('max_datetime', max_datetime))

    # If there is only a single possible date, `just` is more efficient
    if allow_naive and not timezones:
        if min_datetime == max_datetime:
            return just(min_datetime)
    elif not allow_naive and len(timezones) == 1:
        to_tz = timezones[0]
        return just(to_tz.normalize(min_datetime.astimezone(to_tz)))

    return DatetimeStrategy(
        allow_naive=allow_naive, timezones=timezones,
        min_datetime=min_datetime, max_datetime=max_datetime,
    )


@defines_strategy
def dates(min_year=None, max_year=None, min_date=None, max_date=None):
    """Return a strategy for generating dates.

    All values will be dates between ``min_date`` or ``max_date``.  If the
    deprecated ``min_year`` or ``max_year`` arguments are given, they are
    converted to the first and last date of that year respectively.

    .. doctest::

        >>> dates().example()
        datetime.date(100, 12, 19)
        >>> dates().example()
        datetime.date(5621, 7, 9)

    """
    # Handle deprecation and conversion of min_year and max_year arguments
    if (min_year is not None) or (max_year is not None):
        if (min_date is not None) or (max_date is not None):
            raise InvalidArgument(
                'You cannot mix old-style (min_year/max_year) and new-style '
                '(min_date/max_date) arguments to the date strategy.')
        msg = ('The %s argument is deprecated.  Please use %s_date '
               'with a datetime.date object instead.')
        if min_year is not None:
            note_deprecation(msg % ('min_year', 'min'))
            min_date = dt.date.min.replace(year=min_year)
        if max_year is not None:
            note_deprecation(msg % ('max_year', 'max'))
            max_date = dt.date.max.replace(year=max_year)
    del min_year
    del max_year
    # This is part of the deprecation logic - we could just use these immutable
    # objects as default arguments, but we need to distinguish whether a new
    # argument was given by the user for deprecation errors.
    if min_date is None:
        min_date = dt.date.min
    if max_date is None:
        max_date = dt.date.max

    # Discard any time and timezone data - here we're dealing in naive dates
    if isinstance(min_date, dt.datetime):
        min_date = min_date.date()
    if isinstance(max_date, dt.datetime):
        max_date = max_date.date()
    # Check that our bounds are of the correct type, and ordered correctly
    if not isinstance(min_date, dt.date):
        raise InvalidArgument('min_date must be a datetime.date object.')
    if not isinstance(max_date, dt.date):
        raise InvalidArgument('max_date must be a datetime.date object.')
    check_valid_interval(min_date, max_date, 'min_date', 'max_date')

    # If there is only a single possible date, `just` is more efficient
    if min_date == max_date:
        return just(min_date)
    return datetimes(
        allow_naive=True, timezones=[],
        min_datetime=min_date, max_datetime=max_date
    ).map(dt.datetime.date)


@defines_strategy
def times(allow_naive=None, timezones=None,
          min_time=dt.time.min, max_time=dt.time.max):
    """Return a strategy for generating times.

    allow_naive and timezones are interpreted as for naive bounds in
    :py:func:`datetimes`.  min_time and max_time must be naive datetime.time
    objects.  Tz-aware bounds are not supported for the time strategy.

    .. doctest::
        >>> times().example()
        datetime.time(19, 19, 39, 919036, tzinfo=<...>)
        >>> times().example()
        datetime.time(22, 31, 45, 811336, tzinfo=<...>)

    """
    msg = '%s=%r must be a datetime.time object.'
    if not isinstance(min_time, dt.time):
        raise InvalidArgument(msg % ('min_time', min_time))
    if not isinstance(max_time, dt.time):
        raise InvalidArgument(msg % ('max_time', max_time))
    if min_time.tzinfo is not None:
        raise InvalidArgument('min_time=%r must not have tzinfo' % min_time)
    if max_time.tzinfo is not None:
        raise InvalidArgument('max_time=%r must not have tzinfo' % max_time)
    if min_time == max_time:
        return just(min_time)
    check_valid_interval(min_time, max_time, 'min_time', 'max_time')
    day = dt.date(2000, 1, 1)
    return datetimes(
        allow_naive=allow_naive, timezones=timezones,
        min_datetime=dt.datetime.combine(day, min_time),
        max_datetime=dt.datetime.combine(day, max_time)
    ).map(lambda t: t.timetz())
