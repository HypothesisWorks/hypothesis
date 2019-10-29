# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Most of this work is copyright (C) 2013-2019 David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
# CONTRIBUTING.rst for a full list of people who may hold copyright, and
# consult the git log if you need to determine who owns an individual
# contribution.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.
#
# END HEADER

from __future__ import absolute_import, division, print_function

from random import Random

import hypothesis.strategies as st
from hypothesis import (
    HealthCheck,
    Phase,
    Verbosity,
    assume,
    example,
    given,
    reject,
    settings,
)
from hypothesis.internal.compat import hbytes
from hypothesis.internal.conjecture.data import ConjectureData, Status, StopTest
from hypothesis.internal.conjecture.engine import ConjectureRunner
from hypothesis.searchstrategy.numbers import WideRangeIntStrategy


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
        except (StopTest, IndexError):
            pass
        else:
            if stop > 0 and k > 0:
                return (draw(st.integers(0, k - 1)), hbytes(d.buffer))


@example((2, b"\x00\x00\n\x01"))
@example((1, b"\x00\x00\x06\x01"))
@example(problem=(32768, b"\x03\x01\x00\x00\x00\x00\x00\x01\x00\x02\x01"))
@settings(
    suppress_health_check=HealthCheck.all(),
    deadline=None,
    max_examples=10,
    verbosity=Verbosity.normal,
)
@given(problems())
def test_always_reduces_integers_to_smallest_suitable_sizes(problem):
    n, blob = problem
    blob = hbytes(blob)
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

    runner = ConjectureRunner(
        f,
        random=Random(0),
        settings=settings(
            suppress_health_check=HealthCheck.all(),
            phases=(Phase.shrink,),
            database=None,
            verbosity=Verbosity.debug,
        ),
        database_key=None,
    )

    runner.cached_test_function(blob)

    assert runner.interesting_examples

    (v,) = runner.interesting_examples.values()

    shrinker = runner.new_shrinker(v, lambda x: x.status == Status.INTERESTING)

    shrinker.fixate_shrink_passes(["minimize_individual_blocks"])

    v = shrinker.shrink_target

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
    bits_needed = 1 + n.bit_length()
    actual_bits_needed = min(
        [s for s in WideRangeIntStrategy.sizes if s >= bits_needed]
    )
    bytes_needed = actual_bits_needed // 8
    # 3 extra bytes: two for the sampler, one for the capping value.
    assert len(v.buffer) == 3 + bytes_needed
