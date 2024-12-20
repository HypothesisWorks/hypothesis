# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

from random import Random

from hypothesis import assume, example, given, strategies as st
from hypothesis.errors import StopTest
from hypothesis.internal.conjecture.data import ConjectureData, Status
from hypothesis.internal.conjecture.engine import ConjectureRunner


@st.composite
def integer_buffer(draw):
    for _ in range(100):
        buf = draw(st.binary(min_size=8))
        try:
            data = ConjectureData.for_buffer(buf)
            data.draw_integer()
            return bytes(data.buffer)
        except StopTest:
            continue
    assume(False)


@example(
    n=-46,
    buffer=b"f\x00\x01\x01\x01",
)
@given(st.integers(), integer_buffer())
def test_will_always_shrink_an_integer_to_a_boundary(n, buffer):
    if n > 0:

        def test_function(data):
            if data.draw_integer() >= n:
                data.mark_interesting()

    elif n < 0:

        def test_function(data):
            if data.draw_integer() <= n:
                data.mark_interesting()

    else:

        def test_function(data):
            data.draw_integer()
            data.mark_interesting()

    runner = ConjectureRunner(test_function, random=Random(0))
    assume(runner.cached_test_function(buffer).status == Status.INTERESTING)

    runner.shrink_interesting_examples()

    (shrunk,) = runner.interesting_examples.values()

    result = ConjectureData.for_buffer(shrunk.buffer).draw_integer()
    assert result == n
