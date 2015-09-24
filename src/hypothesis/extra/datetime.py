# coding=utf-8

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# Most of this work is copyright (C) 2013-2015 David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
# https://github.com/DRMacIver/hypothesis/blob/master/CONTRIBUTING.rst for a
# full list of people who may hold copyright, and consult the git log if you
# need to determine who owns an individual contribution.

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

from __future__ import division, print_function, absolute_import

import datetime as dt
from collections import namedtuple

import pytz
import hypothesis.internal.distributions as dist
from hypothesis.errors import InvalidArgument
from hypothesis.strategies import defines_strategy
from hypothesis.internal.compat import hrange, text_type
from hypothesis.searchstrategy.strategies import BadData, strategy, \
    check_length, SearchStrategy, check_data_type

DatetimeSpec = namedtuple(u'DatetimeSpec', (u'naive_options',))

naive_datetime = DatetimeSpec(set((True,)))
timezone_aware_datetime = DatetimeSpec(set((False,)))
any_datetime = DatetimeSpec(set((False, True)))


def draw_day_for_month(random, year, month):
    # Validate that we've not got a bad year or month
    dt.datetime(year=year, month=month, day=27)
    for max_day in hrange(31, 27, -1):  # pragma: no branch
        try:
            dt.datetime(year=year, month=month, day=max_day)
            return random.randint(1, max_day)
        except ValueError:
            pass


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
        while True:
            random = random
            year = random.randint(self.min_year, self.max_year)
            month = random.choice(pv.month)
            base = dt.datetime(
                year=year,
                month=month,
                day=draw_day_for_month(random, year, month),
                hour=maybe_zero_or(random, pv.p_hour, random.randint(0, 23)),
                minute=maybe_zero_or(
                    random, pv.p_minute, random.randint(0, 59)),
                second=maybe_zero_or(
                    random, pv.p_second, random.randint(0, 59)),
                microsecond=random.randint(0, 1000000 - 1),
            )
            try:
                if not pv.timezones:
                    return self.templateize(base)

                timezone = random.choice(pv.timezones)

                if not self.allow_naive:
                    return self.templateize(timezone.localize(base))

                naive = random.random() <= pv.naive_chance
                if naive:
                    return self.templateize(base)
                else:
                    return self.templateize(timezone.localize(base))
            except OverflowError:
                pass

    def is_valid_template(self, template):
        if not (self.min_year <= template[0] <= self.max_year):
            return False
        tz = template[-1]
        if tz is None:
            return self.allow_naive
        else:
            if not any(
                text_type(z.zone) == tz
                for z in self.timezones
            ):
                return False
            try:
                self.reify(template)
                return True
            # This is covered but hard to hit reliably
            except (OverflowError, ValueError):  # pragma: no cover
                return False

    def templateize(self, dt):
        return (
            dt.year,
            dt.month,
            dt.day,
            dt.hour,
            dt.minute,
            dt.second,
            dt.microsecond,
            text_type(dt.tzinfo.zone) if dt.tzinfo else None,
        )

    def reify(self, template):
        tz = template[-1]
        d = dt.datetime(
            year=template[0], month=template[1], day=template[2],
            hour=template[3], minute=template[4], second=template[5],
            microsecond=template[6]
        )
        if tz:
            d = pytz.timezone(tz).localize(d)
        return d

    def simplifiers(self, random, template):
        yield self.simplify_timezones
        yield self.simplify_towards_2000

    def simplify_timezones(self, random, value):
        value = self.reify(value)
        if self.timezones:
            if not value.tzinfo:
                yield self.templateize(self.timezones[0].localize(value))
            else:
                # This loop will never exit normally because it breaks when it
                # hits the value.
                for j in hrange(len(self.timezones)):  # pragma: no branch
                    tz = self.timezones[j]
                    if tz.zone == value.tzinfo.zone:
                        break
                    yield self.templateize(tz.normalize(value.astimezone(tz)))

    def year_in_bounds(self, year):
        return self.min_year <= year <= self.max_year

    def simplify_towards_2000(self, random, value):
        value = self.reify(value)
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
            yield self.templateize(t)

        for h in hrange(value.hour - 1, 0, -1):
            yield self.templateize(value.replace(hour=h))

        year = value.year
        if year == 2000:
            return
        # We swallow a bunch of value errors here.
        # These can happen if the original value was february 29 on a
        # leap year and the current year is not a leap year.
        # Note that 2000 was a leap year which is why we didn't need one above.
        mid = (year + 2000) // 2
        if mid != 2000 and mid != year and self.year_in_bounds(mid):
            try:
                yield self.templateize(value.replace(year=mid))
            except ValueError:
                pass
        direction = -1 if year > 2000 else 1
        years = hrange(year + direction, 2000, direction)
        for year in years:
            if year == mid:
                continue
            try:
                if self.year_in_bounds(year):
                    yield self.templateize(value.replace(year))
            except ValueError:
                pass

    def to_basic(self, value):
        return list(value)

    def from_basic(self, values):
        check_data_type(list, values)
        check_length(8, values)
        for d in values[:-1]:
            check_data_type(int, d)
        if values[-1] is not None:
            check_data_type(text_type, values[-1])
        template = tuple(values)
        if not self.is_valid_template(template):
            raise BadData(u'Invalid template %r' % (
                template,
            ))
        return template


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
