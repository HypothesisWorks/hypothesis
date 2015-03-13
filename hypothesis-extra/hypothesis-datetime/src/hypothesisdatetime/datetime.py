# coding=utf-8

# Copyright (C) 2013-2015 David R. MacIver (david@drmaciver.com)

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

from __future__ import division, print_function, absolute_import, \
    unicode_literals

import datetime as dt
from collections import namedtuple

import pytz
import hypothesis.internal.distributions as dist
from hypothesis.searchstrategy import SearchStrategy, strategy, \
    check_data_type
from hypothesis.internal.compat import hrange, text_type
from hypothesis.internal.fixers import equal
from hypothesis.internal.hashitanyway import normal_hash, hash_everything

DatetimeSpec = namedtuple('DatetimeSpec', ('naive_options',))

naive_datetime = DatetimeSpec({True})
timezone_aware_datetime = DatetimeSpec({False})
any_datetime = DatetimeSpec({False, True})


@equal.extend(dt.datetime)
def equal_datetimes(x, y, fuzzy=False):
    return (x.tzinfo == y.tzinfo) and (x == y)

hash_everything.extend(dt.datetime)(normal_hash)


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
        'Parameter',
        (
            'p_hour',
            'p_minute',
            'p_second',
            'month',
            'naive_chance',
            'utc_chance',
            'timezones',
            'naive_options',
        )
    )

    def __init__(self, naive_options=None):
        self.naive_options = naive_options or {False, True}
        if self.naive_options == {False, True}:
            self.descriptor = dt.datetime
        else:
            self.descriptor = DatetimeSpec(self.naive_options)

    def produce_parameter(self, random):
        return self.Parameter(
            p_hour=dist.uniform_float(random, 0, 1),
            p_minute=dist.uniform_float(random, 0, 1),
            p_second=dist.uniform_float(random, 0, 1),
            month=dist.non_empty_subset(random, list(range(1, 13))),
            naive_chance=dist.uniform_float(random, 0, 0.5),
            utc_chance=dist.uniform_float(random, 0, 1),
            timezones=dist.non_empty_subset(
                random,
                list(
                    map(pytz.timezone, pytz.all_timezones))
            ),
            naive_options=dist.non_empty_subset(random,
                                                self.naive_options
                                                )
        )

    def produce_template(self, context, pv):
        random = context.random
        year = random.randint(dt.MINYEAR, dt.MAXYEAR)
        month = random.choice(pv.month)
        base = dt.datetime(
            year=year,
            month=month,
            day=draw_day_for_month(random, year, month),
            hour=maybe_zero_or(random, pv.p_hour, random.randint(0, 23)),
            minute=maybe_zero_or(random, pv.p_minute, random.randint(0, 59)),
            second=maybe_zero_or(random, pv.p_second, random.randint(0, 59)),
            microsecond=random.randint(0, 1000000 - 1),
        )
        if not self.supports_timezones():
            return base

        if random.random() <= pv.utc_chance:
            timezone = pytz.UTC
        else:
            timezone = random.choice(pv.timezones)

        if not self.supports_naive():
            return timezone.localize(base)

        if len(pv.naive_options) == 1:
            naive = list(pv.naive_options)[0]
        else:
            naive = random.random() <= pv.naive_chance

        if naive:
            return base
        else:
            return timezone.localize(base)

    def supports_timezones(self):
        return False in self.naive_options

    def supports_naive(self):
        return True in self.naive_options

    def simplify(self, value):
        if self.supports_timezones():
            if not value.tzinfo:
                yield pytz.UTC.localize(value)
            elif value.tzinfo != pytz.UTC:
                yield pytz.UTC.normalize(value.astimezone(pytz.UTC))
        s = {value}
        s.add(value.replace(microsecond=0))
        s.add(value.replace(second=0))
        s.add(value.replace(minute=0))
        s.add(value.replace(hour=0))
        s.add(value.replace(day=1))
        s.add(value.replace(month=1))
        s.add(value.replace(year=2000))
        s.remove(value)
        for t in s:
            yield t
        year = value.year
        if year == 2000:
            return
        # We swallow a bunch of value errors here.
        # These can happen if the original value was february 29 on a
        # leap year and the current year is not a leap year.
        # Note that 2000 was a leap year which is why we didn't need one above.
        mid = (year + 2000) // 2
        if mid != 2000 and mid != year:
            try:
                yield value.replace(year=mid)
            except ValueError:
                pass
        direction = -1 if year > 2000 else 1
        years = hrange(year + direction, 2000, direction)
        for year in years:
            if year == mid:
                continue
            try:
                yield value.replace(year)
            except ValueError:
                pass

    def to_basic(self, value):
        return [
            value.year, value.month, value.day,
            value.hour, value.minute, value.second,
            value.microsecond,
            text_type(value.tzinfo.zone) if value.tzinfo else None
        ]

    def from_basic(self, values):
        check_data_type(list, values)
        for d in values[:-1]:
            check_data_type(int, d)
        timezone = None
        if values[-1] is not None:
            check_data_type(text_type, values[-1])
            timezone = pytz.timezone(values[-1])
        base = dt.datetime(
            year=values[0], month=values[1], day=values[2],
            hour=values[3], minute=values[4], second=values[5],
            microsecond=values[6]
        )
        if timezone is not None:
            base = timezone.localize(base)
        return base


@strategy.extend_static(dt.datetime)
def datetime_strategy(cls, settings):
    return DatetimeStrategy()


@strategy.extend(DatetimeSpec)
def datetime_specced_strategy(spec, settings):
    return DatetimeStrategy(spec.naive_options)
