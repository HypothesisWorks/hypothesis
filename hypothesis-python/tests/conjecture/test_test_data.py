# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Most of this work is copyright (C) 2013-2020 David R. MacIver
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

import itertools

import pytest

from hypothesis import given, strategies as st
from hypothesis.errors import Frozen, InvalidArgument
from hypothesis.internal.conjecture.data import (
    MAX_DEPTH,
    ConjectureData,
    DataObserver,
    Overrun,
    Status,
    StopTest,
    structural_coverage,
)
from hypothesis.strategies._internal.strategies import SearchStrategy


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
    x = ConjectureData.for_buffer(bytes(5))
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
    x = ConjectureData.for_buffer(b"")
    with pytest.raises(StopTest):
        x.mark_interesting()
    assert x.frozen
    assert x.status == Status.INTERESTING


def test_drawing_zero_bits_is_free():
    x = ConjectureData.for_buffer(b"")
    assert x.draw_bits(0) == 0


def test_can_mark_invalid():
    x = ConjectureData.for_buffer(b"")
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

    d.write(bytes([2]))
    d.freeze()

    def eg(u, v):
        return [ex for ex in d.examples if ex.start == u and ex.end == v][0]

    assert not eg(0, 2).trivial
    assert not eg(0, 1).trivial
    assert eg(1, 2).trivial
    assert eg(2, 3).trivial


def test_example_depth_marking():
    d = ConjectureData.for_buffer(bytes(24))

    # These draw sizes are chosen so that each example has a unique length.
    d.draw_bytes(2)
    d.start_example("inner")
    d.draw_bytes(3)
    d.draw_bytes(6)
    d.stop_example()
    d.draw_bytes(12)
    d.freeze()

    assert len(d.examples) == 6

    depths = {(ex.length, ex.depth) for ex in d.examples}
    assert depths == {(2, 1), (3, 2), (6, 2), (9, 1), (12, 1), (23, 0)}


def test_has_examples_even_when_empty():
    d = ConjectureData.for_buffer(b"")
    d.draw(st.just(False))
    d.freeze()
    assert d.examples


def test_has_cached_examples_even_when_overrun():
    d = ConjectureData.for_buffer(bytes(1))
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
    d.write(b"")
    d.draw_bits(1)
    d.draw_bits(0, forced=0)
    d.draw_bits(1)
    assert d.buffer == bytes([1, 1, 1])


def test_blocks_preserve_identity():
    n = 10
    d = ConjectureData.for_buffer([1] * 10)
    for _ in range(n):
        d.draw_bits(1)
    d.freeze()
    blocks = [d.blocks[i] for i in range(n)]
    result = d.as_result()
    for i, b in enumerate(blocks):
        assert result.blocks[i] is b


def test_compact_blocks_during_generation():
    d = ConjectureData.for_buffer([1] * 10)
    for _ in range(5):
        d.draw_bits(1)
    assert len(list(d.blocks)) == 5
    for _ in range(5):
        d.draw_bits(1)
    assert len(list(d.blocks)) == 10


def test_handles_indices_like_a_list():
    n = 5
    d = ConjectureData.for_buffer([1] * n)
    for _ in range(n):
        d.draw_bits(1)
    assert d.blocks[-1] is d.blocks[n - 1]
    assert d.blocks[-n] is d.blocks[0]

    with pytest.raises(IndexError):
        d.blocks[n]

    with pytest.raises(IndexError):
        d.blocks[-n - 1]


def test_can_observe_draws():
    class LoggingObserver(DataObserver):
        def __init__(self):
            self.log = []

        def draw_bits(self, *args):
            self.log.append(("draw",) + args)

        def conclude_test(self, *args):
            assert x.frozen
            self.log.append(("concluded",) + args)

    observer = LoggingObserver()
    x = ConjectureData.for_buffer(bytes([1, 2, 3]), observer=observer)

    x.draw_bits(1)
    x.draw_bits(7, forced=10)
    x.draw_bits(8)
    with pytest.raises(StopTest):
        x.conclude_test(Status.INTERESTING, interesting_origin="neat")

    assert observer.log == [
        ("draw", 1, False, 1),
        ("draw", 7, True, 10),
        ("draw", 8, False, 3),
        ("concluded", Status.INTERESTING, "neat"),
    ]


def test_calls_concluded_implicitly():
    class NoteConcluded(DataObserver):
        def conclude_test(self, status, reason):
            assert x.frozen
            self.conclusion = (status, reason)

    observer = NoteConcluded()

    x = ConjectureData.for_buffer(bytes([1]), observer=observer)
    x.draw_bits(1)
    x.freeze()

    assert observer.conclusion == (Status.VALID, None)


def test_handles_start_indices_like_a_list():
    n = 5
    d = ConjectureData.for_buffer([1] * n)
    for _ in range(n):
        d.draw_bits(1)

    for i in range(-2 * n, 2 * n + 1):
        try:
            start = d.blocks.start(i)
        except IndexError:
            # Directly retrieving the start position failed, so check that
            # indexing also fails.
            with pytest.raises(IndexError):
                d.blocks[i]
            continue

        # Directly retrieving the start position succeeded, so check that
        # indexing also succeeds, and gives the same position.
        assert start == d.blocks[i].start


def test_last_block_length():
    d = ConjectureData.for_buffer([0] * 15)

    with pytest.raises(IndexError):
        d.blocks.last_block_length

    for n in range(1, 5 + 1):
        d.draw_bits(n * 8)
        assert d.blocks.last_block_length == n


def test_examples_show_up_as_discarded():
    d = ConjectureData.for_buffer([1, 0, 1])

    d.start_example(1)
    d.draw_bits(1)
    d.stop_example(discard=True)
    d.start_example(1)
    d.draw_bits(1)
    d.stop_example()
    d.freeze()

    assert len([ex for ex in d.examples if ex.discarded]) == 1


def test_examples_support_negative_indexing():
    d = ConjectureData.for_buffer(bytes(2))
    d.draw_bits(1)
    d.draw_bits(1)
    d.freeze()
    assert d.examples[-1].length == 1


def test_can_override_label():
    d = ConjectureData.for_buffer(bytes(2))
    d.draw(st.booleans(), label=7)
    d.freeze()
    assert any(ex.label == 7 for ex in d.examples)


def test_will_mark_too_deep_examples_as_invalid():
    d = ConjectureData.for_buffer(bytes(0))

    s = st.none()
    for _ in range(MAX_DEPTH + 1):
        s = s.map(lambda x: x)

    with pytest.raises(StopTest):
        d.draw(s)
    assert d.status == Status.INVALID


def test_empty_strategy_is_invalid():
    d = ConjectureData.for_buffer(bytes(0))
    with pytest.raises(StopTest):
        d.draw(st.nothing())
    assert d.status == Status.INVALID


def test_will_error_on_find():
    d = ConjectureData.for_buffer(bytes(0))
    d.is_find = True
    with pytest.raises(InvalidArgument):
        d.draw(st.data())


def test_can_note_non_str():
    d = ConjectureData.for_buffer(bytes(0))
    x = object()
    d.note(x)
    assert repr(x) in d.output


def test_can_note_str_as_non_repr():
    d = ConjectureData.for_buffer(bytes(0))
    d.note("foo")
    assert d.output == "foo"


def test_result_is_overrun():
    d = ConjectureData.for_buffer(bytes(0))
    with pytest.raises(StopTest):
        d.draw_bits(1)
    assert d.as_result() is Overrun


def test_trivial_before_force_agrees_with_trivial_after():
    d = ConjectureData.for_buffer([0, 1, 1])
    d.draw_bits(1)
    d.draw_bits(1, forced=1)
    d.draw_bits(1)

    t1 = [d.blocks.trivial(i) for i in range(3)]
    d.freeze()
    r = d.as_result()
    t2 = [b.trivial for b in r.blocks]
    assert d.blocks.owner is None
    t3 = [r.blocks.trivial(i) for i in range(3)]

    assert t1 == t2 == t3


def test_events_are_noted():
    d = ConjectureData.for_buffer(())
    d.note_event("hello")
    assert "hello" in d.events


def test_blocks_end_points():
    d = ConjectureData.for_buffer(bytes(4))
    d.draw_bits(1)
    d.draw_bits(16, forced=1)
    d.draw_bits(8)
    assert (
        list(d.blocks.all_bounds())
        == [b.bounds for b in d.blocks]
        == [(0, 1), (1, 3), (3, 4)]
    )


def test_blocks_lengths():
    d = ConjectureData.for_buffer(bytes(7))
    d.draw_bits(32)
    d.draw_bits(16)
    d.draw_bits(1)
    assert [b.length for b in d.blocks] == [4, 2, 1]


def test_child_indices():
    d = ConjectureData.for_buffer(bytes(4))

    d.start_example(0)  # examples[1]
    d.start_example(0)  # examples[2]
    d.draw_bits(1)  # examples[3]
    d.draw_bits(1)  # examples[4]
    d.stop_example()
    d.stop_example()
    d.draw_bits(1)  # examples[5]
    d.draw_bits(1)  # examples[6]
    d.freeze()

    assert list(d.examples.children[0]) == [1, 5, 6]
    assert list(d.examples.children[1]) == [2]
    assert list(d.examples.children[2]) == [3, 4]

    assert d.examples[0].parent is None
    for ex in list(d.examples)[1:]:
        assert ex in d.examples[ex.parent].children


def test_example_equality():
    d = ConjectureData.for_buffer(bytes(2))

    d.start_example(0)
    d.draw_bits(1)
    d.stop_example()
    d.start_example(0)
    d.draw_bits(1)
    d.stop_example()
    d.freeze()

    examples = list(d.examples)
    for ex1, ex2 in itertools.combinations(examples, 2):
        assert ex1 != ex2
        assert not (ex1 == ex2)

    for ex in examples:
        assert ex == ex
        not (ex != ex)

        assert not (ex == "hello")
        assert ex != "hello"


@given(st.integers(0, 255), st.randoms(use_true_random=True))
def test_partial_buffer(n, rnd):
    data = ConjectureData(prefix=[n], random=rnd, max_length=2)

    assert data.draw_bytes(2)[0] == n


def test_structural_coverage_is_cached():
    assert structural_coverage(50) is structural_coverage(50)


def test_examples_create_structural_coverage():
    data = ConjectureData.for_buffer(bytes(0))
    data.start_example(42)
    data.stop_example()
    data.freeze()
    assert structural_coverage(42) in data.tags


def test_discarded_examples_do_not_create_structural_coverage():
    data = ConjectureData.for_buffer(bytes(0))
    data.start_example(42)
    data.stop_example(discard=True)
    data.freeze()
    assert structural_coverage(42) not in data.tags


def test_children_of_discarded_examples_do_not_create_structural_coverage():
    data = ConjectureData.for_buffer(bytes(0))
    data.start_example(10)
    data.start_example(42)
    data.stop_example()
    data.stop_example(discard=True)
    data.freeze()
    assert structural_coverage(42) not in data.tags
    assert structural_coverage(10) not in data.tags
