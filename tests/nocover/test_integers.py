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

from random import Random

import hypothesis.strategies as st
from hypothesis import Phase, Verbosity, note, given, assume, reject, \
    settings, unlimited
from hypothesis.internal.compat import ceil, hbytes
from hypothesis.internal.conjecture.data import StopTest, ConjectureData
from hypothesis.internal.conjecture.engine import ConjectureRunner


@st.composite
def problems(draw):
    while True:
        buf = bytearray(draw(st.binary(min_size=16, max_size=16)))
        while buf and not buf[-1]:
            buf.pop()
        try:
            d = ConjectureData.for_buffer(buf)
            k = d.draw(st.integers())
            stop = d.draw_bits(8)
            if stop > 0 and k > 0:
                return (draw(st.integers(0, k - 1)), hbytes(d.buffer))
        except (StopTest, IndexError):
            pass


@settings(
    perform_health_check=False, timeout=unlimited, deadline=None,
)
@given(problems())
def test_always_reduces_integers_to_smallest_suitable_sizes(problem):
    n, blob = problem
    try:
        d = ConjectureData.for_buffer(blob)
        k = d.draw(st.integers())
        stop = blob[len(d.buffer)]
    except (StopTest, IndexError):
        reject()

    assume(k > n)
    assume(stop > 0)

    def f(data):
        k = data.draw(st.integers())
        data.output = repr(k)
        if data.draw_bits(8) == stop and k >= n:
            data.mark_interesting()

    runner = ConjectureRunner(f, random=Random(0), settings=settings(
        perform_health_check=False, timeout=unlimited, phases=(Phase.shrink,),
        database=None, verbosity=Verbosity.quiet
    ))

    runner.test_function(ConjectureData.for_buffer(blob))

    assert runner.interesting_examples

    runner.run()

    v, = runner.interesting_examples.values()

    runner.debug = note
    runner.debug_data(v)

    m = ConjectureData.for_buffer(v.buffer).draw(st.integers())
    assert m == n

    # Upper bound on the length needed is calculated as follows:
    # * We have an initial byte at the beginning to decide the length of the
    #   integer.
    # * We have a terminal byte as the stop value.
    # * The rest is the integer payload. This should be n. Including the sign
    #   bit, n needs (1 + n.bit_length()) / 8 bytes (rounded up). But we only
    #   have power of two sizes, so it may be up to a factor of two more than
    #   that.
    assert len(v.buffer) <= 2 + 2 * max(1, ceil((1 + n.bit_length()) / 8))
