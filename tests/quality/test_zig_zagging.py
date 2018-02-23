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

import hypothesis.strategies as st
from hypothesis import Verbosity, note, given, assume, example, settings
from hypothesis.internal.compat import hbytes, int_from_bytes
from hypothesis.internal.conjecture.data import Status, ConjectureData
from hypothesis.internal.conjecture.engine import ConjectureRunner


@st.composite
def problem(draw):
    b = hbytes(draw(st.binary(min_size=1, max_size=8)))
    m = int_from_bytes(b) * 256
    assume(m > 0)
    marker = draw(st.binary(max_size=8))
    bound = draw(st.integers(0, m - 1))
    return (b, marker, bound)


@example((b'\x01\x00', b'', 20048))
@example((b'\x02', b'', 258))
@example((b'\x08', b'', 1792))
@example((b'\x0c', b'', 0))
@example((b'\x01', b'', 1))
@example((b'\x01', b'', 0))
@settings(
    deadline=None, perform_health_check=False, max_examples=10,
    max_shrinks=100
)
@given(problem())
def test_avoids_zig_zag_trap(p):
    b, marker, lower_bound = p
    b = hbytes(b)
    marker = hbytes(marker)

    n_bits = 8 * (len(b) + 1)

    def test_function(data):
        m = data.draw_bits(n_bits)
        if m < lower_bound:
            data.mark_invalid()
        n = data.draw_bits(n_bits)
        if data.draw_bytes(len(marker)) != marker:
            data.mark_invalid()
        if abs(m - n) == 1:
            data.mark_interesting()

    runner = ConjectureRunner(
        test_function, database_key=None, settings=settings(
            database=None, max_shrinks=100, verbosity=Verbosity.debug
        )
    )

    runner.debug = note
    original_debug_data = runner.debug_data

    def debug_interesting(data):
        if data.status == Status.INTERESTING:
            original_debug_data(data)
    runner.debug_data = debug_interesting

    runner.test_function(ConjectureData.for_buffer(
        b + hbytes([0]) + b + hbytes([1]) + marker))

    assert runner.interesting_examples

    runner.run()

    v, = runner.interesting_examples.values()

    data = ConjectureData.for_buffer(v.buffer)

    m = data.draw_bits(n_bits)
    n = data.draw_bits(n_bits)
    assert m == lower_bound
    if m == 0:
        assert n == 1
    else:
        assert n == m - 1
