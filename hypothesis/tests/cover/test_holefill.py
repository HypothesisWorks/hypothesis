# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import itertools
from random import Random

import pytest

from hypothesis import settings, strategies as st
from hypothesis.control import BuildContext
from hypothesis.internal.conjecture.choice import HoleRecord, ValueHole
from hypothesis.internal.conjecture.data import ConjectureData
from hypothesis.internal.holefill import distance_fills, fill_prefix
from hypothesis.strategies._internal.lazy import unwrap_strategies

pytestmark = pytest.mark.skipif(
    settings().backend == "crosshair", reason="cannot _invert symbolic values"
)


def draw_from_choices(strategy, choices):
    data = ConjectureData.for_choices(choices)
    with BuildContext(data, wrapped_test=lambda: None):
        return data.draw(strategy)


def solve(strategy, target, budget=50, seed=0):
    """Iterate distance_fills until a fill regenerates ``target`` exactly."""
    records = [HoleRecord(index=0, strategy=strategy, value=target)]
    for fills in itertools.islice(distance_fills(records, Random(seed)), budget):
        (fill,) = fills
        if draw_from_choices(strategy, fill) == target:
            return fill
    return None


def test_replay_records_all_unclaimed_holes():
    strategy = st.tuples(
        st.integers(), st.integers().map(str), st.booleans(), st.text().map(str.title)
    )
    value = (5, "6", True, "Hi")
    prefix = strategy._invert_with_holes(value)
    assert prefix == (
        5,
        ValueHole("6", record=True),
        True,
        ValueHole("Hi", record=True),
    )

    data = ConjectureData(random=Random(0), prefix=prefix)
    with BuildContext(data, wrapped_test=lambda: None):
        drawn = data.draw(strategy)

    # both unclaimed holes were recorded in a single replay, at the choice
    # index where the declining strategy began drawing...
    assert [(record.index, record.value) for record in data.hole_records] == [
        (1, "6"),
        (3, "Hi"),
    ]
    # ...and the concrete parts of the prefix stayed aligned around the
    # freshly-drawn hole segments
    assert data.misaligned_at is None
    assert drawn[0] == 5
    assert drawn[2] is True


def test_recorded_strategy_regenerates_the_hole():
    strategy = st.lists(st.integers().map(str), min_size=1, max_size=2)
    prefix = strategy._invert_with_holes(["5"])
    assert prefix == (True, ValueHole("5", record=True), False)
    data = ConjectureData(random=Random(0), prefix=prefix)
    with BuildContext(data, wrapped_test=lambda: None):
        data.draw(strategy)
    (record,) = data.hole_records
    assert record.value == "5"
    # the recorded strategy is the mapped element strategy, so drawing from
    # it can regenerate the target value
    assert draw_from_choices(record.strategy, (5,)) == "5"


def test_hole_at_a_zero_choice_offset_records_the_outermost_strategy():
    # min_size == max_size means the list draws no size choices before its
    # first element, so the list strategy itself is the first to decline the
    # hole - and is recorded, covering the whole span at that position.
    strategy = st.lists(st.integers().map(str), min_size=1, max_size=1)
    prefix = strategy._invert_with_holes(["5"])
    assert prefix == (ValueHole("5", record=True),)
    data = ConjectureData(random=Random(0), prefix=prefix)
    with BuildContext(data, wrapped_test=lambda: None):
        data.draw(strategy)
    (record,) = data.hole_records
    assert record.strategy is unwrap_strategies(strategy)
    assert draw_from_choices(record.strategy, (5,)) == ["5"]


def test_unrecorded_holes_still_degrade_to_misalignment():
    # a plain ValueHole (record=False, as used by the shrinker's widening
    # pass) keeps its existing semantics: no record, and misaligned_at set
    # when no strategy claims it
    strategy = st.integers().map(str)
    data = ConjectureData(random=Random(0), prefix=(ValueHole(("un", "claimable")),))
    with BuildContext(data, wrapped_test=lambda: None):
        data.draw(strategy)
    assert data.hole_records == []
    assert data.misaligned_at is not None


def test_fill_prefix_replaces_holes_in_order():
    prefix = (1, ValueHole("a", record=True), 2, ValueHole("b", record=True))
    assert fill_prefix(prefix, [(5, 6), (7,)]) == (1, 5, 6, 2, 7)


def test_distance_search_fills_mapped_hole():
    assert solve(st.integers().map(lambda x: x * 2), 10) == (5,)


def test_distance_search_fills_composite_hole():
    @st.composite
    def points(draw):
        return (draw(st.integers(0, 5)), draw(st.integers(0, 5)))

    assert solve(points(), (3, 4)) == (3, 4)


def test_distance_search_fills_flatmapped_hole():
    strategy = st.integers(1, 3).flatmap(
        lambda n: st.lists(st.integers(0, 5), min_size=n, max_size=n)
    )
    fill = solve(strategy, [1, 2])
    assert draw_from_choices(strategy, fill) == [1, 2]


def test_distance_search_fills_all_holes_per_candidate():
    records = [
        HoleRecord(index=0, strategy=st.integers().map(lambda x: x * 2), value=10),
        HoleRecord(index=1, strategy=st.integers().map(str), value="7"),
    ]
    for fills in itertools.islice(distance_fills(records, Random(0)), 50):
        assert len(fills) == len(records)
        values = [
            draw_from_choices(record.strategy, fill)
            for record, fill in zip(records, fills, strict=True)
        ]
        if values == [10, "7"]:
            return
    raise AssertionError("search did not fill both holes")


def test_distance_search_terminates_on_tiny_domains():
    # with only two possible values the search runs out of new candidates
    # and ends, rather than looping forever
    records = [HoleRecord(index=0, strategy=st.booleans().map(str), value="maybe")]
    fills = list(distance_fills(records, Random(0)))
    assert 1 <= len(fills) <= 10
