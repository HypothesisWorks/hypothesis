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

import struct

from hypothesis.internal.floats import sign
from hypothesis.searchstrategy.strategies import SearchStrategy, \
    MappedSearchStrategy
from hypothesis.internal.conjecture.grammar import Literal, Interval, \
    Negation, Wildcard, Alternation, Intersection, Concatenation


def _allowed_bytes(ls):
    return Alternation(Literal(bytes([l])) for l in ls)


def _filtered_bytes(f):
    return _allowed_bytes(filter(f, range(256)))


ANY_FLOAT = Wildcard(8)

NEGATIVE_FLOAT = Concatenation([
    _filtered_bytes(lambda b: b >> 7),
    Wildcard(7)
]).normalize()


def _one_of_floats(ls):
    return Alternation([
        Literal(struct.pack('!d', f)) for f in ls
    ])

INFINITY = _one_of_floats([
    float('inf'), float('-inf'),
])

NAN = Concatenation([
    _allowed_bytes([127, 255]),
    _filtered_bytes(lambda b: b >> 3 == 0b11111),
    Wildcard(6),
])


NASTY_FLOATS = _one_of_floats(
    sign * x
    for sign in [-1, 1]
    for x in [
        0.0, 0.5, 1.0 / 3, 10e6, 10e-6, 1.175494351e-38,
        2.2250738585072014e-308,
        1.7976931348623157e+308, 3.402823466e+38, 9007199254740992, 1 - 10e-6,
        2 + 10e-6, 1.192092896e-07, 2.2204460492503131e-016,
    ]
)

BASE_WEIGHTS = [
    (ANY_FLOAT, 2),
    (NASTY_FLOATS, 5),
    (INFINITY, 8), (NAN, 1),
]


class FloatStrategy(SearchStrategy):

    """Generic superclass for strategies which produce floats."""

    def __init__(self, allow_infinity, allow_nan):
        assert isinstance(allow_infinity, bool)
        assert isinstance(allow_nan, bool)
        SearchStrategy.__init__(self)
        base = ANY_FLOAT
        if not allow_infinity:
            base = Intersection([base, Negation(INFINITY)])
        if not allow_nan:
            base = Intersection([base, Negation(NAN)])
        base = base.normalize()

        self.weights = [2, 5]
        self.grammars = [base, NASTY_FLOATS]
        if allow_infinity:
            self.weights.append(5)
            self.grammars.append(INFINITY)
        if allow_nan:
            self.weights.append(2)
            self.grammars.append(NAN)

    def do_draw(self, data):
        g = self.grammars[data.draw_byte(self.weights)]
        buf = data.draw_from_grammar(g)
        assert len(buf) == 8, (buf, g)
        return struct.unpack('!d', buf)[0]


def float_order_key(k):
    return (sign(k), k)


class FixedBoundedFloatStrategy(SearchStrategy):

    """A strategy for floats distributed between two endpoints.

    The conditional distribution tries to produce values clustered
    closer to one of the ends.

    """

    def __init__(self, lower_bound, upper_bound):
        SearchStrategy.__init__(self)
        self.lower_bound = float(lower_bound)
        self.upper_bound = float(upper_bound)
        assert sign(self.lower_bound) == sign(self.upper_bound)
        lb = float_order_key(self.lower_bound)
        ub = float_order_key(self.upper_bound)

        critical = [
            z for z in (-0.0, 0.0)
            if lb <= float_order_key(z) <= ub
        ]
        critical.append(self.lower_bound)
        critical.append(self.upper_bound)
        self.grammars = [
            Interval(*sorted(struct.pack(
                '!d', f) for f in (self.lower_bound, self.upper_bound))),
            _one_of_floats(critical),
        ]

    def __repr__(self):
        return 'FixedBoundedFloatStrategy(%s, %s)' % (
            self.lower_bound, self.upper_bound,
        )

    def do_draw(self, data):
        g = self.grammars[data.draw_byte((1, 1))]
        return struct.unpack('!d', data.draw_from_grammar(g))[0]


class ComplexStrategy(MappedSearchStrategy):

    """A strategy over complex numbers, with real and imaginary values
    distributed according to some provided strategy for floating point
    numbers."""

    def __repr__(self):
        return 'ComplexStrategy()'

    def pack(self, value):
        return complex(*value)
