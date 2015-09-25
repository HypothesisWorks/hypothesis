# coding=utf-8

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# Most of this work is copyright (C) 2013-2015 David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
# https://github.com/DRMacIver/hypothesis/blob/master/CONTRIBUTING.rst for a
# full list of people who may hold copyright, and consult the git log if you
# need to determine who owns an individual contribution.

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

from __future__ import division, print_function, absolute_import

import hypothesis.internal.distributions as dist
from hypothesis.types import RandomWithSeed
from hypothesis.internal.compat import hrange, integer_types
from hypothesis.searchstrategy.strategies import BadData, check_type, \
    SearchStrategy, check_data_type, MappedSearchStrategy


class BoolStrategy(SearchStrategy):

    """A strategy that produces Booleans with a Bernoulli conditional
    distribution."""
    template_upper_bound = 2

    def __repr__(self):
        return u'BoolStrategy()'

    def reify(self, value):
        return value

    def strictly_simpler(self, x, y):
        return (not x) and y

    def basic_simplify(self, random, value):
        if value:
            yield False

    def draw_parameter(self, random):
        return random.random()

    def draw_template(self, random, p):
        return dist.biased_coin(random, p)

    def to_basic(self, value):
        check_type(bool, value)
        return int(value)

    def from_basic(self, value):
        check_data_type(int, value)
        return bool(value)


class JustStrategy(SearchStrategy):

    """
    A strategy which simply returns a single fixed value with probability 1.
    """
    template_upper_bound = 1

    def __init__(self, value):
        SearchStrategy.__init__(self)
        self.value = value

    def __repr__(self):
        return u'JustStrategy(value=%r)' % (self.value,)

    def draw_parameter(self, random):
        return None

    def draw_template(self, random, pv):
        return None

    def reify(self, template):
        assert template is None
        return self.value

    def simplifiers(self, random, template):
        return ()

    def to_basic(self, template):
        return None

    def from_basic(self, data):
        if data is not None:
            raise BadData(u'Expected None but got %r' % (repr(data,)))
        return None


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
        self.elements = tuple(elements)
        self.template_upper_bound = len(self.elements)
        assert self.elements

    def to_basic(self, template):
        return template

    def from_basic(self, data):
        check_data_type(integer_types, data)
        if data < 0:
            raise BadData(u'Index out of range: %d < 0' % (data,))
        elif data >= len(self.elements):
            raise BadData(
                u'Index out of range: %d >= %d' % (data, len(self.elements)))

        return data

    def basic_simplify(self, random, template):
        for i in hrange(0, template):
            yield i

    def strictly_simpler(self, x, y):
        return x < y

    def __repr__(self):
        return u'SampledFromStrategy(%r)' % (self.elements,)

    def draw_parameter(self, random):
        n = len(self.elements)
        return [
            random.randint(0, n - 1) for _ in hrange(n)
        ]

    def draw_template(self, random, pv):
        return random.choice(pv)

    def reify(self, template):
        return self.elements[template]
