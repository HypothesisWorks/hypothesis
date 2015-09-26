# coding=utf-8
#
# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)
#
# Most of this work is copyright (C) 2013-2015 David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
# https://github.com/DRMacIver/hypothesis/blob/master/CONTRIBUTING.rst for a
# full list of people who may hold copyright, and consult the git log if you
# need to determine who owns an individual contribution.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.
#
# END HEADER

from __future__ import division, print_function, absolute_import

import datetime as dt
from collections import namedtuple

import pytz

import hypothesis.internal.distributions as dist
from hypothesis.errors import InvalidArgument
from hypothesis.control import assume
from hypothesis.strategies import defines_strategy
from hypothesis.internal.compat import hrange, text_type
from hypothesis.internal.strategymethod import strategy
from hypothesis.searchstrategy.strategies import BadData, check_length, \
    SearchStrategy, check_data_type

DatetimeSpec = namedtuple(u'DatetimeSpec', (u'naive_options',))

naive_datetime = DatetimeSpec(set((True,)))
timezone_aware_datetime = DatetimeSpec(set((False,)))
any_datetime = DatetimeSpec(set((False, True)))


class DateTimeTemplate(namedtuple('DateTimeTemplate', (
    'year', 'month', 'day', 'hour', 'minute', 'second', 'microsecond',
    'tzinfo'
))):

    def replace(self, **kwargs):
        data = list(self)
        for k, v in kwargs.items():
            data[self._fields.index(k)] = v
        return DateTimeTemplate(*data)

    def to_datetime(self):
        d = dt.datetime(**dict(
            (k, getattr(self, k)) for k in self._fields[:-1]
        ))
        if self.tzinfo is not None:
            d = self.tzinfo.localize(d)
        return d

    def __trackas__(self):
        data = list(self)
        if data[-1] is not None:
            data[-1] = text_type(data[-1].zone)
        return data


def maybe_zero_or(random, p, v):
    if random.random() <= p:
        return v
    else:
        return 0


class DatetimeStrategy(SearchStrategy):

    Parameter = namedtuple(
        u'Parameter',
        (
            u'p_hour',
            u'p_minute',
            u'p_second',
            u'month',
            u'naive_chance',
            u'timezones',
        )
    )

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

    def draw_parameter(self, random):
        return self.Parameter(
            p_hour=dist.uniform_float(random, 0, 1),
            p_minute=dist.uniform_float(random, 0, 1),
            p_second=dist.uniform_float(random, 0, 1),
            month=dist.non_empty_subset(random, list(range(1, 13))),
            naive_chance=dist.uniform_float(random, 0, 0.5),
            timezones=self.timezones and dist.non_empty_subset(
                random, self.timezones),
        )

    def draw_template(self, random, pv):
        if not pv.timezones:
            timezone = None
        else:
            timezone = random.choice(pv.timezones)
            if self.allow_naive and random.random() <= pv.naive_chance:
                timezone = None

        return DateTimeTemplate(
            year=random.randint(self.min_year, self.max_year),
            month=random.choice(pv.month),
            day=random.randint(1, 31),
            hour=maybe_zero_or(random, pv.p_hour, random.randint(0, 23)),
            minute=maybe_zero_or(
                random, pv.p_minute, random.randint(0, 59)),
            second=maybe_zero_or(
                random, pv.p_second, random.randint(0, 59)),
            microsecond=random.randint(0, 1000000 - 1),
            tzinfo=timezone,
        )

    def reify(self, template):
        assume(self.min_year <= template.year <= self.max_year)
        tz = template[-1]
        if tz is None:
            assume(self.allow_naive)
        else:
            assume(template.tzinfo in self.timezones)
        try:
            return template.to_datetime()
        except (OverflowError, ValueError):
            assume(False)

    def simplifiers(self, random, template):
        yield self.simplify_timezones
        yield self.simplify_towards_2000

    def simplify_timezones(self, random, template):
        if self.timezones:
            if template.tzinfo is None:
                for t in self.timezones:
                    yield template.replace(tzinfo=t)
            else:
                # This loop will never exit normally because it breaks when it
                # hits the value.
                for tz in self.timezones:  # pragma: no branch
                    if tz.zone == template.tzinfo.zone:
                        break
                    yield template.replace(tzinfo=tz)

    def year_in_bounds(self, year):
        return self.min_year <= year <= self.max_year

    def simplify_towards_2000(self, random, value):
        s = set((value,))
        s.add(value.replace(microsecond=0))
        s.add(value.replace(second=0))
        s.add(value.replace(minute=0))
        s.add(value.replace(hour=0))
        s.add(value.replace(day=1))
        s.add(value.replace(month=1))
        if self.year_in_bounds(2000):
            s.add(value.replace(year=2000))
        s.remove(value)
        for t in s:
            yield t

        for h in hrange(value.hour - 1, 0, -1):
            yield value.replace(hour=h)

        year = value.year
        if year == 2000:
            return
        # We swallow a bunch of value errors here.
        # These can happen if the original value was february 29 on a
        # leap year and the current year is not a leap year.
        # Note that 2000 was a leap year which is why we didn't need one above.
        mid = (year + 2000) // 2
        if mid != 2000 and mid != year and self.year_in_bounds(mid):
            yield value.replace(year=mid)
        direction = -1 if year > 2000 else 1
        years = hrange(year + direction, 2000, direction)
        for year in years:
            if year == mid:
                continue
            if self.year_in_bounds(year):
                yield value.replace(year=year)

    def to_basic(self, value):
        return value.__trackas__()

    def from_basic(self, values):
        check_data_type(list, values)
        values = list(values)
        check_length(8, values)
        for d in values[:-1]:
            check_data_type(int, d)
        if values[-1] is not None:
            check_data_type(text_type, values[-1])
            try:
                values[-1] = pytz.timezone(values[-1])
            except pytz.UnknownTimeZoneError as e:
                raise BadData(*e.args)
        return DateTimeTemplate(*values)


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


@strategy.extend_static(dt.datetime)
def datetime_strategy(cls, settings):
    return datetimes()


@strategy.extend(DatetimeSpec)
def datetime_specced_strategy(spec, settings):  # pragma: no cover
    if not spec.naive_options:
        raise InvalidArgument(
            u'Must allow either naive or non-naive datetimes')
    return datetimes(
        allow_naive=(True in spec.naive_options),
        timezones=(None if False in spec.naive_options else [])
    )
