# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

"""Reaching the minimum here needs two elements to move at once.

``st.binary`` and ``st.text`` are each a single choice, shrunk by ``Collection``
rather than by the node-level passes which handle ``st.lists`` and ``st.tuples``,
so ``Collection`` has to cover this case itself.
"""

from hypothesis.internal.conjecture.shrinking import Bytes, String
from hypothesis.internal.intervalsets import IntervalSet

from tests.conjecture.common import interesting_origin, shrinking_from

# The shortlex-minimal value satisfying `unsorted_bytes`: everything below it
# starts b"\x00\x00", and b"\x00\x00\x00" / b"\x00\x00\x01" are both sorted.
MINIMUM = b"\x00\x01\x00"
# Getting to MINIMUM from here means lowering index 1 (2 -> 1) and index 2
# (1 -> 0) together. Neither moves alone: b"\x00\x01\x01" and b"\x00\x00\x01"
# are sorted, and b"\x00\x02\x00" has no 0x01.
TWO_MOVE_START = b"\x00\x02\x01"

# "abc" shrink in alphabetical order, so these mirror the bytes case exactly.
ALPHABET = IntervalSet.from_string("abc")
TEXT_MINIMUM = "aba"
TEXT_TWO_MOVE_START = "acb"


def unsorted_bytes(value):
    """A three-byte value containing 0x01 which is not in sorted order.

    The length check mirrors the ``max_size=3`` constraint that the engine
    enforces for us in the ``shrinking_from`` tests below, but which the
    standalone ``Bytes`` shrinker (which only takes ``min_size``) does not.
    """
    return len(value) == 3 and b"\x01" in value and list(value) != sorted(value)


def unsorted_text(value):
    """The ``unsorted_bytes`` predicate over "abc" instead of bytes."""
    return len(value) == 3 and "b" in value and list(value) != sorted(value)


def test_bytes_shrinker_lowers_an_element_and_its_suffix_together():
    shrunk = Bytes.shrink(TWO_MOVE_START, unsorted_bytes, full=True, min_size=3)
    assert bytes(shrunk) == MINIMUM


def test_bytes_shrinker_reaches_the_minimum_from_elsewhere():
    shrunk = Bytes.shrink(b"\x01\x00\x00", unsorted_bytes, full=True, min_size=3)
    assert bytes(shrunk) == MINIMUM


def test_string_shrinker_lowers_an_element_and_its_suffix_together():
    shrunk = String.shrink(
        TEXT_TWO_MOVE_START, unsorted_text, full=True, intervals=ALPHABET, min_size=3
    )
    assert "".join(shrunk) == TEXT_MINIMUM


def test_string_shrinker_reaches_the_minimum_from_elsewhere():
    shrunk = String.shrink(
        "baa", unsorted_text, full=True, intervals=ALPHABET, min_size=3
    )
    assert "".join(shrunk) == TEXT_MINIMUM


def test_shrinker_lowers_a_bytes_element_and_its_suffix_together():
    @shrinking_from((TWO_MOVE_START,))
    def shrinker(data):
        if unsorted_bytes(data.draw_bytes(min_size=3, max_size=3)):
            data.mark_interesting(interesting_origin())

    shrinker.shrink()
    assert shrinker.choices == (MINIMUM,)


def test_shrinker_lowers_a_string_element_and_its_suffix_together():
    @shrinking_from((TEXT_TWO_MOVE_START,))
    def shrinker(data):
        if unsorted_text(data.draw_string(ALPHABET, min_size=3, max_size=3)):
            data.mark_interesting(interesting_origin())

    shrinker.shrink()
    assert shrinker.choices == (TEXT_MINIMUM,)


def test_shrinker_reaches_the_minimum_from_elsewhere():
    @shrinking_from((b"\x01\x00\x00",))
    def shrinker(data):
        if unsorted_bytes(data.draw_bytes(min_size=3, max_size=3)):
            data.mark_interesting(interesting_origin())

    shrinker.shrink()
    assert shrinker.choices == (MINIMUM,)
