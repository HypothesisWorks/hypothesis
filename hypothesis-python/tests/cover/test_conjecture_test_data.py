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

import pytest

from hypothesis import given, strategies as st
from hypothesis.errors import Frozen
from hypothesis.internal.compat import hbytes, hrange
from hypothesis.internal.conjecture.data import ConjectureData, Status, StopTest
from hypothesis.searchstrategy.strategies import SearchStrategy


@given(st.binary())
def test_buffer_draws_as_self(buf):
    x = ConjectureData.for_buffer(buf)
    assert x.draw_bytes(len(buf)) == buf


def test_cannot_draw_after_freeze():
    x = ConjectureData.for_buffer(b"hi")
    x.draw_bytes(1)
    x.freeze()
    with pytest.raises(Frozen):
        x.draw_bytes(1)


def test_can_double_freeze():
    x = ConjectureData.for_buffer(b"hi")
    x.freeze()
    assert x.frozen
    x.freeze()
    assert x.frozen


def test_can_draw_zero_bytes():
    x = ConjectureData.for_buffer(b"")
    for _ in range(10):
        assert x.draw_bytes(0) == b""


def test_draw_past_end_sets_overflow():
    x = ConjectureData.for_buffer(hbytes(5))
    with pytest.raises(StopTest) as e:
        x.draw_bytes(6)
    assert e.value.testcounter == x.testcounter
    assert x.frozen
    assert x.status == Status.OVERRUN


def test_notes_repr():
    x = ConjectureData.for_buffer(b"")
    x.note(b"hi")
    assert repr(b"hi") in x.output


def test_can_mark_interesting():
    x = ConjectureData.for_buffer(hbytes())
    with pytest.raises(StopTest):
        x.mark_interesting()
    assert x.frozen
    assert x.status == Status.INTERESTING


def test_drawing_zero_bits_is_free():
    x = ConjectureData.for_buffer(hbytes())
    assert x.draw_bits(0) == 0


def test_can_mark_invalid():
    x = ConjectureData.for_buffer(hbytes())
    with pytest.raises(StopTest):
        x.mark_invalid()
    assert x.frozen
    assert x.status == Status.INVALID


class BoomStrategy(SearchStrategy):
    def do_draw(self, data):
        data.draw_bytes(1)
        raise ValueError()


def test_closes_interval_on_error_in_strategy():
    x = ConjectureData.for_buffer(b"hi")
    with pytest.raises(ValueError):
        x.draw(BoomStrategy())
    x.freeze()
    assert not any(eg.end is None for eg in x.examples)


class BigStrategy(SearchStrategy):
    def do_draw(self, data):
        data.draw_bytes(10 ** 6)


def test_does_not_double_freeze_in_interval_close():
    x = ConjectureData.for_buffer(b"hi")
    with pytest.raises(StopTest):
        x.draw(BigStrategy())
    assert x.frozen
    assert not any(eg.end is None for eg in x.examples)


def test_triviality():
    d = ConjectureData.for_buffer([1, 0, 1])

    d.start_example(1)
    d.draw_bits(1)
    d.draw_bits(1)
    d.stop_example(1)

    d.write(hbytes([2]))
    d.freeze()

    def eg(u, v):
        return [ex for ex in d.examples if ex.start == u and ex.end == v][0]

    assert not eg(0, 2).trivial
    assert not eg(0, 1).trivial
    assert eg(1, 2).trivial
    assert eg(2, 3).trivial


def test_example_depth_marking():
    d = ConjectureData.for_buffer(hbytes(24))

    # These draw sizes are chosen so that each example has a unique length.
    d.draw_bytes(2)
    d.start_example("inner")
    d.draw_bytes(3)
    d.draw_bytes(6)
    d.stop_example()
    d.draw_bytes(12)
    d.freeze()

    depths = set((ex.length, ex.depth) for ex in d.examples)
    assert depths == set([(2, 1), (3, 2), (6, 2), (9, 1), (12, 1), (23, 0)])


def test_has_examples_even_when_empty():
    d = ConjectureData.for_buffer(hbytes())
    d.draw(st.just(False))
    d.freeze()
    assert d.examples


def test_has_cached_examples_even_when_overrun():
    d = ConjectureData.for_buffer(hbytes(1))
    d.start_example(3)
    d.draw_bits(1)
    d.stop_example()
    try:
        d.draw_bits(1)
    except StopTest:
        pass
    assert d.status == Status.OVERRUN
    assert any(ex.label == 3 and ex.length == 1 for ex in d.examples)
    assert d.examples is d.examples


def test_can_write_empty_string():
    d = ConjectureData.for_buffer([1, 1, 1])
    d.draw_bits(1)
    d.write(hbytes())
    d.draw_bits(1)
    d.draw_bits(0, forced=0)
    d.draw_bits(1)
    assert d.buffer == hbytes([1, 1, 1])


def test_blocks_preserve_identity():
    n = 10
    d = ConjectureData.for_buffer([1] * 10)
    for _ in hrange(n):
        d.draw_bits(1)
    d.freeze()
    blocks = [d.blocks[i] for i in range(n)]
    result = d.as_result()
    for i, b in enumerate(blocks):
        assert result.blocks[i] is b


def test_compact_blocks_during_generation():
    d = ConjectureData.for_buffer([1] * 10)
    for _ in hrange(5):
        d.draw_bits(1)
    assert len(list(d.blocks)) == 5
    for _ in hrange(5):
        d.draw_bits(1)
    assert len(list(d.blocks)) == 10


def test_handles_indices_like_a_list():
    n = 5
    d = ConjectureData.for_buffer([1] * n)
    for _ in hrange(n):
        d.draw_bits(1)
    assert d.blocks[-1] is d.blocks[n - 1]
    assert d.blocks[-n] is d.blocks[0]

    with pytest.raises(IndexError):
        d.blocks[n]

    with pytest.raises(IndexError):
        d.blocks[-n - 1]
