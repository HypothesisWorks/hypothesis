# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2018 David R. MacIver
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

"""
--------------------
hypothesis[datetime]
--------------------

This module provides deprecated time and date related strategies.

It depends on the ``pytz`` package, which is stable enough that almost any
version should be compatible - most updates are for the timezone database.
"""

from __future__ import division, print_function, absolute_import

import datetime as dt

import pytz

import hypothesis.strategies as st
from hypothesis.errors import InvalidArgument
from hypothesis._settings import note_deprecation
from hypothesis.extra.pytz import timezones as timezones_strategy

__all__ = ['datetimes', 'dates', 'times']


def tz_args_strat(allow_naive, tz_list, name):
    if tz_list is None:
        tz_strat = timezones_strategy()
    else:
        tz_strat = st.sampled_from([
            tz if isinstance(tz, dt.tzinfo) else pytz.timezone(tz)
            for tz in tz_list
        ])
    if allow_naive or (allow_naive is None and tz_strat.is_empty):
        tz_strat = st.none() | tz_strat
    if tz_strat.is_empty:
        raise InvalidArgument(
            'Cannot create non-naive %s with no timezones allowed.' % name)
    return tz_strat


def convert_year_bound(val, default):
    if val is None:
        return default
    try:
        return default.replace(val)
    except ValueError:
        raise InvalidArgument('Invalid year=%r' % (val,))


@st.defines_strategy
def datetimes(allow_naive=None, timezones=None, min_year=None, max_year=None):
    """Return a strategy for generating datetimes.

    .. deprecated:: 3.9.0
        use :py:func:`hypothesis.strategies.datetimes` instead.

    allow_naive=True will cause the values to sometimes be naive.
    timezones is the set of permissible timezones. If set to an empty
    collection all datetimes will be naive. If set to None all timezones
    available via pytz will be used.

    All generated datetimes will be between min_year and max_year, inclusive.
    """
    note_deprecation('Use hypothesis.strategies.datetimes, which supports '
                     'full-precision bounds and has a simpler API.')
    min_dt = convert_year_bound(min_year, dt.datetime.min)
    max_dt = convert_year_bound(max_year, dt.datetime.max)
    tzs = tz_args_strat(allow_naive, timezones, 'datetimes')
    return st.datetimes(min_dt, max_dt, tzs)


@st.defines_strategy
def dates(min_year=None, max_year=None):
    """Return a strategy for generating dates.

    .. deprecated:: 3.9.0
        use :py:func:`hypothesis.strategies.dates` instead.

    All generated dates will be between min_year and max_year, inclusive.
    """
    note_deprecation('Use hypothesis.strategies.dates, which supports bounds '
                     'given as date objects for single-day resolution.')
    return st.dates(convert_year_bound(min_year, dt.date.min),
                    convert_year_bound(max_year, dt.date.max))


@st.defines_strategy
def times(allow_naive=None, timezones=None):
    """Return a strategy for generating times.

    .. deprecated:: 3.9.0
        use :py:func:`hypothesis.strategies.times` instead.

    The allow_naive and timezones arguments act the same as the datetimes
    strategy above.
    """
    note_deprecation('Use hypothesis.strategies.times, which supports '
                     'min_time and max_time arguments.')
    return st.times(timezones=tz_args_strat(allow_naive, timezones, 'times'))
