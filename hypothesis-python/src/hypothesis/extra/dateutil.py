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

from dateutil import zoneinfo, tz

import hypothesis.strategies as st

__all__ = ['timezones']


@st.cacheable
@st.defines_strategy
def timezones():
    # type: () -> st.SearchStrategy[dt.tzinfo]
    """Any timezone in dateutil.

    This strategy minimises to UTC, or the smallest possible fixed
    offset, and is designed for use with
    :py:func:`hypothesis.strategies.datetimes`.
    """
    reference_date = dt.datetime(2000, 1, 1)
    return st.sampled_from([tz.UTC] + sorted(
        zoneinfo.get_zonefile_instance().zones.values(),
        key=lambda zone: abs(zone.utcoffset(reference_date))
    ))
