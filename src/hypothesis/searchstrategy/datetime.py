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

from __future__ import division, print_function, absolute_import

import datetime as dt

from hypothesis.internal.conjecture import utils
from hypothesis.searchstrategy.strategies import SearchStrategy

__all__ = ['DateStrategy', 'DatetimeStrategy', 'TimedeltaStrategy']


def is_pytz_timezone(tz):
    if not isinstance(tz, dt.tzinfo):
        return False
    module = type(tz).__module__
    return module == 'pytz' or module.startswith('pytz.')


class DatetimeStrategy(SearchStrategy):

    def __init__(self, min_datetime, max_datetime, timezones_strat):
        assert isinstance(min_datetime, dt.datetime)
        assert isinstance(max_datetime, dt.datetime)
        assert min_datetime.tzinfo is None
        assert max_datetime.tzinfo is None
        assert min_datetime <= max_datetime
        assert isinstance(timezones_strat, SearchStrategy)
        self.min_dt = min_datetime
        self.max_dt = max_datetime
        self.tz_strat = timezones_strat

    def _attempt_one_draw(self, data):
        result = dict()
        cap_low, cap_high = True, True
        for name in ('year', 'month', 'day',
                     'hour', 'minute', 'second', 'microsecond'):
            low = getattr(self.min_dt if cap_low else dt.datetime.min, name)
            high = getattr(self.max_dt if cap_high else dt.datetime.max, name)
            if name == 'year':
                val = utils.centered_integer_range(data, low, high, 2000)
            else:
                val = utils.integer_range(data, low, high)
            result[name] = val
            cap_low = cap_low and val == low
            cap_high = cap_high and val == high
        tz = data.draw(self.tz_strat)
        try:
            result = dt.datetime(**result)
            if is_pytz_timezone(tz):
                # Can't just construct; see http://pytz.sourceforge.net
                return tz.normalize(tz.localize(result))
            return result.replace(tzinfo=tz)
        except (ValueError, OverflowError):
            return None

    def do_draw(self, data):
        for _ in range(3):
            result = self._attempt_one_draw(data)
            if result is not None:
                return result
        data.note_event('3 attempts to create a datetime between %r and %r '
                        'with timezone from %r failed.' %
                        (self.min_dt, self.max_dt, self.tz_strat))
        data.mark_invalid()


class DateStrategy(SearchStrategy):

    def __init__(self, min_date, max_date):
        assert isinstance(min_date, dt.date)
        assert isinstance(max_date, dt.date)
        assert min_date < max_date
        self.min_date = min_date
        self.days_apart = (max_date - min_date).days
        self.center = (dt.date(2000, 1, 1) - min_date).days

    def do_draw(self, data):
        return self.min_date + dt.timedelta(days=utils.centered_integer_range(
            data, 0, self.days_apart, center=self.center))


class TimedeltaStrategy(SearchStrategy):

    def __init__(self, min_delta, max_delta):
        assert isinstance(min_delta, dt.timedelta)
        assert isinstance(max_delta, dt.timedelta)
        assert min_delta < max_delta
        self.min_delta = min_delta
        self.max_delta = max_delta

    def do_draw(self, data):
        result = dict()
        low_bound = True
        high_bound = True
        for name in ('days', 'seconds', 'microseconds'):
            low = getattr(
                self.min_delta if low_bound else dt.timedelta.min, name)
            high = getattr(
                self.max_delta if high_bound else dt.timedelta.max, name)
            val = utils.centered_integer_range(data, low, high, 0)
            result[name] = val
            low_bound = low_bound and val == low
            high_bound = high_bound and val == high
        return dt.timedelta(**result)
