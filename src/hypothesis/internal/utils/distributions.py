# coding=utf-8

# Copyright (C) 2013-2015 David R. MacIver (david@drmaciver.com)

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

from __future__ import division, print_function, unicode_literals

import math


def geometric(random, p):
    """Generate a geometric integer in the range [0, infinity) with expected
    value.

    1 / p - 1

    """
    denom = math.log1p(-p)
    return int(math.log(random.random()) / denom)


def biased_coin(random, p):
    return random.random() <= p
