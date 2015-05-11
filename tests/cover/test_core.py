from __future__ import division, print_function, absolute_import, \
    unicode_literals

import pytest
import hypothesis.strategies as s
from hypothesis import Settings, find, assume
from hypothesis.errors import NoSuchExample, Unsatisfiable
from hypothesis.internal.tracker import Tracker


def test_stops_after_max_examples_if_satisfying():
    tracker = Tracker()

    def track(x):
        tracker.track(x)
        return False

    max_examples = 100

    with pytest.raises(NoSuchExample):
        find(
            s.integers(0, 10000),
            track, settings=Settings(max_examples=max_examples))

    assert len(tracker) == max_examples


def test_stops_after_max_iterations_if_not_satisfying():
    tracker = Tracker()

    def track(x):
        tracker.track(x)
        assume(False)

    max_examples = 100
    max_iterations = 200

    with pytest.raises(Unsatisfiable):
        find(
            s.integers(0, 10000),
            track, settings=Settings(
                max_examples=max_examples, max_iterations=max_iterations))

    assert len(tracker) == max_iterations
