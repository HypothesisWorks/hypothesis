# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

from math import log
from random import Random

from hypothesis import (
    HealthCheck,
    Phase,
    Verbosity,
    assume,
    example,
    given,
    settings,
    strategies as st,
)
from hypothesis.internal.compat import ceil, int_from_bytes
from hypothesis.internal.conjecture.data import ConjectureData
from hypothesis.internal.conjecture.engine import ConjectureRunner


@st.composite
def problem(draw):
    b = draw(st.binary(min_size=1, max_size=8))
    m = int_from_bytes(b) * 256
    assume(m > 0)
    marker = draw(st.binary(max_size=8))
    bound = draw(st.integers(0, m - 1))
    return (b, marker, bound)


base_settings = settings(
    database=None,
    deadline=None,
    suppress_health_check=list(HealthCheck),
    max_examples=10,
    verbosity=Verbosity.normal,
    phases=(Phase.explicit, Phase.generate),
)


@example((b"\x10\x00\x00\x00\x00\x00", b"", 2861143707951135))
@example((b"\x05Cn", b"%\x1b\xa0\xfa", 12394667))
@example((b"\x179 f", b"\xf5|", 24300326997))
@example((b"\x05*\xf5\xe5\nh", b"", 1076887621690235))
@example((b"=", b"", 2508))
@example((b"\x01\x00", b"", 20048))
@example((b"\x01", b"", 0))
@example((b"\x02", b"", 258))
@example((b"\x08", b"", 1792))
@example((b"\x0c", b"", 0))
@example((b"\x01", b"", 1))
@settings(
    base_settings,
    verbosity=Verbosity.normal,
    phases=(
        # We disable shrinking for this test because when it fails it's a sign
        # that the shrinker is working really badly, so it ends up very slow!
        Phase.explicit,
        Phase.generate,
    ),
    max_examples=20,
)
@given(problem())
def test_avoids_zig_zag_trap(p):
    b, marker, lower_bound = p

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
        test_function,
        database_key=None,
        settings=settings(base_settings, phases=(Phase.generate, Phase.shrink)),
        random=Random(0),
    )

    runner.cached_test_function(b + bytes([0]) + b + bytes([1]) + marker)

    assert runner.interesting_examples

    runner.run()

    (v,) = runner.interesting_examples.values()

    data = ConjectureData.for_buffer(v.buffer)

    m = data.draw_bits(n_bits)
    n = data.draw_bits(n_bits)
    assert m == lower_bound
    if m == 0:
        assert n == 1
    else:
        assert n == m - 1

    budget = 2 * n_bits * ceil(log(n_bits, 2)) + 2

    assert runner.shrinks <= budget
