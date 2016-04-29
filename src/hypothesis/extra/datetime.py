# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2015 David R. MacIver
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

from __future__ import division, print_function, absolute_import

import datetime as dt

import pytz

import hypothesis.internal.conjecture.utils as cu
from hypothesis.errors import InvalidArgument
from hypothesis.strategies import defines_strategy
from hypothesis.searchstrategy.strategies import SearchStrategy


class DatetimeStrategy(SearchStrategy):

    def __init__(self, allow_naive, timezones, min_year=None, max_year=None):
        self.allow_naive = allow_naive
        self.timezones = timezones
        self.min_year = min_year or dt.MINYEAR
        self.max_year = max_year or dt.MAXYEAR
        for a in ['min_year', 'max_year']:
            year = getattr(self, a)
            if year < dt.MINYEAR:
                raise InvalidArgument(u'%s out of range: %d < %d' % (
                    a, year, dt.MINYEAR
                ))
            if year > dt.MAXYEAR:
                raise InvalidArgument(u'%s out of range: %d > %d' % (
                    a, year, dt.MAXYEAR
                ))

    def do_draw(self, data):
        while True:
            try:
                result = dt.datetime(
                    year=cu.centered_integer_range(
                        data, self.min_year, self.max_year, 2000
                    ),
                    month=cu.integer_range(data, 1, 12),
                    day=cu.integer_range(data, 1, 31),
                    hour=cu.integer_range(data, 0, 24),
                    minute=cu.integer_range(data, 0, 59),
                    second=cu.integer_range(data, 0, 59),
                    microsecond=cu.integer_range(data, 0, 999999)
                )
                if (
                    not self.allow_naive or
                    (self.timezones and cu.boolean(data))
                ):
                    result = cu.choice(data, self.timezones).localize(result)
                return result

            except (OverflowError, ValueError):
                pass


@defines_strategy
def datetimes(allow_naive=None, timezones=None, min_year=None, max_year=None):
    """Return a strategy for generating datetimes.

    allow_naive=True will cause the values to sometimes be naive.
    timezones is the set of permissible timezones. If set to an empty
    collection all timezones must be naive. If set to None all available
    timezones will be used.

    """
    if timezones is None:
        timezones = list(pytz.all_timezones)
        timezones.remove(u'UTC')
        timezones.insert(0, u'UTC')
    timezones = [
        tz if isinstance(tz, dt.tzinfo) else pytz.timezone(tz)
        for tz in timezones
    ]
    if allow_naive is None:
        allow_naive = not timezones
    if not (timezones or allow_naive):
        raise InvalidArgument(
            u'Cannot create non-naive datetimes with no timezones allowed'
        )
    return DatetimeStrategy(
        allow_naive=allow_naive, timezones=timezones,
        min_year=min_year, max_year=max_year,
    )


@defines_strategy
def dates(min_year=None, max_year=None):
    """Return a strategy for generating dates."""
    return datetimes(
        allow_naive=True, timezones=[],
        min_year=min_year, max_year=max_year,
    ).map(datetime_to_date)


def datetime_to_date(dt):
    return dt.date()


@defines_strategy
def times(allow_naive=None, timezones=None):
    """Return a strategy for generating times."""
    return datetimes(
        allow_naive=allow_naive, timezones=timezones,
    ).map(datetime_to_time)


def datetime_to_time(dt):
    return dt.timetz()
