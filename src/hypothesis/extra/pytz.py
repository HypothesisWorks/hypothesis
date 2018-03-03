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

"""This module provides ``pytz`` timezones.

You can use this strategy to make
:py:func:`hypothesis.strategies.datetimes` and
:py:func:`hypothesis.strategies.times` produce timezone-aware values.
"""

from __future__ import division, print_function, absolute_import

import datetime as dt

import pytz

import hypothesis.strategies as st

__all__ = ['timezones']


@st.cacheable
@st.defines_strategy
def timezones():
    """Any timezone in the Olsen database, as a pytz tzinfo object.

    This strategy minimises to UTC, or the smallest possible fixed
    offset, and is designed for use with
    :py:func:`hypothesis.strategies.datetimes`.
    """
    all_timezones = [pytz.timezone(tz) for tz in pytz.all_timezones]
    # Some timezones have always had a constant offset from UTC.  This makes
    # them simpler than timezones with daylight savings, and the smaller the
    # absolute offset the simpler they are.  Of course, UTC is even simpler!
    static = [pytz.UTC] + sorted(
        (t for t in all_timezones if isinstance(t, pytz.tzfile.StaticTzInfo)),
        key=lambda tz: abs(tz.utcoffset(dt.datetime(2000, 1, 1)))
    )
    # Timezones which have changed UTC offset; best ordered by name.
    dynamic = [tz for tz in all_timezones if tz not in static]
    return st.sampled_from(static + dynamic)
