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

from hypothesis.internal.compat import hbytes, int_to_bytes, int_from_bytes
from hypothesis.internal.conjecture.floats import is_simple, \
    float_to_lex, lex_to_float
from hypothesis.internal.conjecture.shrinking.common import Shrinker
from hypothesis.internal.conjecture.shrinking.floats import Float
from hypothesis.internal.conjecture.shrinking.integer import Integer
from hypothesis.internal.conjecture.shrinking.ordering import Ordering


"""
This module implements a lexicographic minimizer for blocks of bytes.
"""


class Lexical(Shrinker):
    def make_immutable(self, value):
        return hbytes(value)

    @property
    def size(self):
        return len(self.current)

    def check_invariants(self, value):
        assert len(value) == self.size

    def left_is_better(self, left, right):
        return left < right

    def incorporate_int(self, i):
        return self.incorporate(int_to_bytes(i, self.size))

    def incorporate_float(self, f):
        assert self.size == 8
        return self.incorporate_int(float_to_lex(f))

    def float_hack(self):
        """Our encoding of floating point numbers does the right thing when you
        lexically shrink it, but there are some highly non-obvious lexical
        shrinks corresponding to natural floating point operations.

        We can't actually tell when the floating point encoding is being used
        (that would break the assumptions that Hypothesis doesn't inspect
        the generated values), but we can cheat: We just guess when it might be
        being used and perform shrinks that are valid regardless of our guess
        is correct.

        So that's what this method does. It's a cheat to give us good shrinking
        of floating at low cost in runtime and only moderate cost in elegance.
        """
        # If the block is of the wrong size then we're certainly not using the
        # float encoding.
        if self.size != 8:
            return

        # If the high bit is zero then we're in the integer representation of
        # floats so we don't need these hacks because it will shrink normally.
        if self.current[0] >> 7 == 0:
            return

        i = self.current_int
        f = lex_to_float(i)

        # This floating point number can be represented in our simple format.
        # So we try converting it to that (which will give the same float, but
        # a different encoding of it). If that doesn't work then the float
        # value of this doesn't unambiguously give the desired predicate, so
        # this approach isn't useful. If it *does* work, then we're now in a
        # situation where we don't need it, so either way we return here.
        if is_simple(f):
            self.incorporate_float(f)
            return

        self.delegate(
            Float,
            convert_to=lambda b: lex_to_float(int_from_bytes(b)),
            convert_from=lambda f: int_to_bytes(float_to_lex(f), self.size),
        )

    @property
    def current_int(self):
        return int_from_bytes(self.current)

    def minimize_as_integer(self, full=False):
        Integer.shrink(
            self.current_int,
            lambda c: c == self.current_int or self.incorporate_int(c),
            random=self.random, full=full,
        )

    def partial_sort(self):
        Ordering.shrink(
            self.current, self.consider,
            random=self.random,
        )

    def short_circuit(self):
        """This is just an assemblage of other shrinkers, so we rely on their
        short circuiting."""
        return False

    def run_step(self):
        self.float_hack()
        self.minimize_as_integer()
        self.partial_sort()
