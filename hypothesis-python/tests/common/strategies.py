# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import time

from hypothesis import strategies as st
from hypothesis.internal.intervalsets import IntervalSet
from hypothesis.strategies._internal import SearchStrategy


class _Slow(SearchStrategy):
    def do_draw(self, data):
        time.sleep(1.01)
        data.draw_bytes(2)
        return None


SLOW = _Slow()


class HardToShrink(SearchStrategy):
    def __init__(self):
        self.__last = None
        self.accepted = set()

    def do_draw(self, data):
        x = bytes(data.draw_integer(0, 255) for _ in range(100))
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
        diffs = [i for i in range(len(x)) if x[i] != ls[i]]
        if len(diffs) == 1:
            i = diffs[0]
            if x[i] + 1 == ls[i]:
                self.__last = x
                self.accepted.add(x)
                return True
        return False


def build_intervals(ls):
    ls.sort()
    result = []
    for u, l in ls:
        v = u + l
        if result:
            a, b = result[-1]
            if u <= b + 1:
                result[-1] = (a, v)
                continue
        result.append((u, v))
    return result


def IntervalLists(min_size=0):
    return st.lists(
        st.tuples(st.integers(0, 200), st.integers(0, 20)),
        min_size=min_size,
    ).map(build_intervals)


Intervals = st.builds(IntervalSet, IntervalLists())
