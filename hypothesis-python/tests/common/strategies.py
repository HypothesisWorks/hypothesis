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

from __future__ import division, print_function, absolute_import

import time

from hypothesis.searchstrategy import SearchStrategy
from hypothesis.internal.compat import hrange


class _Slow(SearchStrategy):
    def do_draw(self, data):
        time.sleep(1.0)
        data.draw_bytes(2)
        return None


SLOW = _Slow()


class HardToShrink(SearchStrategy):
    def __init__(self):
        self.__last = None
        self.accepted = set()

    def do_draw(self, data):
        x = data.draw_bytes(100)
        if x in self.accepted:
            return True
        ls = self.__last
        if ls is None:
            if all(x):
                self.__last = x
                self.accepted.add(x)
                return True
            else:
                return False
        diffs = [i for i in hrange(len(x)) if x[i] != ls[i]]
        if len(diffs) == 1:
            i = diffs[0]
            if x[i] + 1 == ls[i]:
                self.__last = x
                self.accepted.add(x)
                return True
        return False
