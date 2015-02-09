# coding=utf-8

# Copyright (C) 2013-2015 David R. MacIver (david@drmaciver.com)

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

from __future__ import division, print_function, unicode_literals

from hypothesis.internal.utils.hashitanyway import HashItAnyway


class Tracker(object):

    def __init__(self):
        self.contents = {}

    def track(self, x):
        k = HashItAnyway(x)
        n = self.contents.get(k, 0) + 1
        self.contents[k] = n
        return n
