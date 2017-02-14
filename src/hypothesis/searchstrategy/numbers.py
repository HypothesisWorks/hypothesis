# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2016 David R. MacIver
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

import hypothesis.internal.conjecture.utils as d
from hypothesis.internal.compat import hbytes, int_from_bytes
from hypothesis.searchstrategy.strategies import SearchStrategy


class IntStrategy(SearchStrategy):

    """A generic strategy for integer types that provides the basic methods
    other than produce.

    Subclasses should provide the produce method.

    """


class IntegersFromStrategy(SearchStrategy):

    def __init__(self, lower_bound, average_size=100000.0):
        super(IntegersFromStrategy, self).__init__()
        self.lower_bound = lower_bound
        self.average_size = average_size

    def __repr__(self):
        return 'IntegersFromStrategy(%d)' % (self.lower_bound,)

    def do_draw(self, data):
        return int(
            self.lower_bound + d.geometric(data, 1.0 / self.average_size))


BYTE_WEIGHTINGS = []

for b in range(16):
    w0 = 1 - 0.5 ** (b + 1)
    BYTE_WEIGHTINGS.append(
        (w0,) + ((1 - w0) / 255,) * 255
    )


# Give the high bit an equal chance of being 0 or 1, so as to spread the
# distribution evenly among negative and positive integers
BYTE_WEIGHTINGS[-1] = list(BYTE_WEIGHTINGS[-1])
BYTE_WEIGHTINGS[-1][128] = BYTE_WEIGHTINGS[-1][0]
BYTE_WEIGHTINGS[-1] = tuple(BYTE_WEIGHTINGS[-1])


class WideRangeIntStrategy(IntStrategy):

    def __repr__(self):
        return 'WideRangeIntStrategy()'

    def do_draw(self, data):
        r = int_from_bytes(hbytes(
            data.draw_byte(b)
            for b in reversed(BYTE_WEIGHTINGS)
        ))
        size = len(BYTE_WEIGHTINGS)
        sign_mask = 2 ** (size * 8 - 1)
        negative = r & sign_mask
        r &= (~sign_mask)
        if negative:
            r = -r
        return int(r)


class BoundedIntStrategy(SearchStrategy):

    """A strategy for providing integers in some interval with inclusive
    endpoints."""

    def __init__(self, start, end):
        SearchStrategy.__init__(self)
        self.start = start
        self.end = end

    def __repr__(self):
        return 'BoundedIntStrategy(%d, %d)' % (self.start, self.end)

    def do_draw(self, data):
        return d.integer_range(data, self.start, self.end)
