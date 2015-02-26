# coding=utf-8

# Copyright (C) 2013-2015 David R. MacIver (david@drmaciver.com)

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

from __future__ import division, print_function, absolute_import, \
    unicode_literals

from hypothesis.searchstrategy.table import StrategyTable
from datetime import datetime


def load():
    from hypothesis.extra.datetime import (
        DatetimeSpec, DatetimeStrategy
    )
    StrategyTable.default().define_specification_for(
        datetime, lambda s, d: DatetimeStrategy()
    )
    StrategyTable.default().define_specification_for_instances(
        DatetimeSpec, lambda s, d: DatetimeStrategy(d.naive_options)
    )
