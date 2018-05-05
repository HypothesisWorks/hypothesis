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

import pytest

from hypothesis import given
from hypothesis import strategies as st
from hypothesis.errors import Frozen
from hypothesis._internal.conjecture.data import Status, StopTest, \
    ConjectureData
from hypothesis._searchstrategy.strategies import SearchStrategy


@given(st.binary())
def test_buffer_draws_as_self(buf):
    x = ConjectureData.for_buffer(buf)
    assert x.draw_bytes(len(buf)) == buf


def test_cannot_draw_after_freeze():
    x = ConjectureData.for_buffer(b'hi')
    x.draw_bytes(1)
    x.freeze()
    with pytest.raises(Frozen):
        x.draw_bytes(1)


def test_can_double_freeze():
    x = ConjectureData.for_buffer(b'hi')
    x.freeze()
    assert x.frozen
    x.freeze()
    assert x.frozen


def test_can_draw_zero_bytes():
    x = ConjectureData.for_buffer(b'')
    for _ in range(10):
        assert x.draw_bytes(0) == b''


def test_draw_past_end_sets_overflow():
    x = ConjectureData.for_buffer(bytes(5))
    with pytest.raises(StopTest) as e:
        x.draw_bytes(6)
    assert e.value.testcounter == x.testcounter
    assert x.frozen
    assert x.status == Status.OVERRUN


def test_notes_repr():
    x = ConjectureData.for_buffer(b'')
    x.note(b'hi')
    assert repr(b'hi') in x.output


def test_can_mark_interesting():
    x = ConjectureData.for_buffer(bytes())
    with pytest.raises(StopTest):
        x.mark_interesting()
    assert x.frozen
    assert x.status == Status.INTERESTING


def test_drawing_zero_bits_is_free():
    x = ConjectureData.for_buffer(bytes())
    assert x.draw_bits(0) == 0


def test_can_mark_invalid():
    x = ConjectureData.for_buffer(bytes())
    with pytest.raises(StopTest):
        x.mark_invalid()
    assert x.frozen
    assert x.status == Status.INVALID


class BoomStrategy(SearchStrategy):

    def do_draw(self, data):
        data.draw_bytes(1)
        raise ValueError()


def test_closes_interval_on_error_in_strategy():
    x = ConjectureData.for_buffer(b'hi')
    with pytest.raises(ValueError):
        x.draw(BoomStrategy())
    x.freeze()
    assert not any(eg.end is None for eg in x.examples)


class BigStrategy(SearchStrategy):

    def do_draw(self, data):
        data.draw_bytes(10 ** 6)


def test_does_not_double_freeze_in_interval_close():
    x = ConjectureData.for_buffer(b'hi')
    with pytest.raises(StopTest):
        x.draw(BigStrategy())
    assert x.frozen
    assert not any(eg.end is None for eg in x.examples)


def test_empty_discards_do_not_count():
    x = ConjectureData.for_buffer(b'')
    x.start_example(label=1)
    x.stop_example(discard=True)
    x.freeze()
    assert not x.has_discards
