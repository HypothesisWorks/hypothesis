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

import hypothesis.internal.conjecture.utils as d
from hypothesis.types import RandomWithSeed
from hypothesis.searchstrategy.strategies import SearchStrategy, \
    MappedSearchStrategy


class BoolStrategy(SearchStrategy):
    """A strategy that produces Booleans with a Bernoulli conditional
    distribution."""

    def __repr__(self):
        return u'BoolStrategy()'

    def calc_has_reusable_values(self, recur):
        return True

    def do_draw(self, data):
        return d.boolean(data)


def is_simple_data(value):
    try:
        hash(value)
        return True
    except TypeError:
        return False


class JustStrategy(SearchStrategy):
    """A strategy which always returns a single fixed value."""

    def __init__(self, value):
        SearchStrategy.__init__(self)
        self.value = value

    def __repr__(self):
        return 'just(%r)' % (self.value,)

    def calc_has_reusable_values(self, recur):
        return True

    def calc_is_cacheable(self, recur):
        return is_simple_data(self.value)

    def do_draw(self, data):
        return self.value


class RandomStrategy(MappedSearchStrategy):
    """A strategy which produces Random objects.

    The conditional distribution is simply a RandomWithSeed seeded with
    a 128 bits of data chosen uniformly at random.

    """

    def pack(self, i):
        return RandomWithSeed(i)


class SampledFromStrategy(SearchStrategy):
    """A strategy which samples from a set of elements. This is essentially
    equivalent to using a OneOfStrategy over Just strategies but may be more
    efficient and convenient.

    The conditional distribution chooses uniformly at random from some
    non-empty subset of the elements.

    """

    def __init__(self, elements):
        SearchStrategy.__init__(self)
        self.elements = d.check_sample(elements)
        assert self.elements

    def calc_has_reusable_values(self, recur):
        return True

    def calc_is_cacheable(self, recur):
        return is_simple_data(self.elements)

    def do_draw(self, data):
        return d.choice(data, self.elements)
