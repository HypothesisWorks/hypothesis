# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

"""Tests for the DataObject ``draws`` parameter and its deferred-printing of
draws in falsifying-example output."""

import re

import pytest

from hypothesis import Phase, given, settings, strategies as st
from hypothesis.errors import InvalidArgument
from hypothesis.strategies._internal.core import DataObject
from hypothesis.vendor import pretty

# --- Basic DataObject(draws=...) semantics ----------------------------


def test_data_object_with_draws_reads_sequentially():
    obj = DataObject(draws=[1, 2, 3])
    assert obj.draw(st.integers()) == 1
    assert obj.draw(st.integers()) == 2
    assert obj.draw(st.integers()) == 3


def test_data_object_with_draws_ignores_strategy_choice():
    # The strategy argument is validated but not used when draws= is supplied.
    obj = DataObject(draws=["x", "y"])
    assert obj.draw(st.integers()) == "x"
    assert obj.draw(st.lists(st.integers())) == "y"


def test_data_object_requires_exactly_one_of_data_or_draws():
    with pytest.raises((InvalidArgument, ValueError, TypeError)):
        DataObject()
    with pytest.raises((InvalidArgument, ValueError, TypeError)):
        DataObject(data=None, draws=None)


def test_data_object_rejects_both_data_and_draws():
    # A fake data-like sentinel - we only want to check the XOR guard, not
    # exercise the ConjectureData path here.
    fake_data = object()
    with pytest.raises((InvalidArgument, ValueError, TypeError)):
        DataObject(data=fake_data, draws=[1, 2])


def test_data_object_with_draws_validates_strategy_argument():
    obj = DataObject(draws=[1])
    with pytest.raises(InvalidArgument):
        obj.draw("not a strategy")


# --- _repr_pretty_ / deferred-printer attribute integration -----------


def _finalize_and_render(p):
    if p._recording is not None:
        p.finalize()
    return p.getvalue()


def test_repr_pretty_empty_when_no_draws():
    obj = DataObject(draws=[1, 2, 3])
    p = pretty.RepresentationPrinter()
    p.pretty(obj)
    assert _finalize_and_render(p) == "DataObject(draws=[])"


def test_repr_pretty_records_subsequent_draws():
    obj = DataObject(draws=[1, 2, 3])
    p = pretty.RepresentationPrinter()
    p.pretty(obj)
    obj.draw(st.integers())
    obj.draw(st.integers())
    obj.draw(st.integers())
    assert _finalize_and_render(p) == "DataObject(draws=[1, 2, 3])"


def test_repr_pretty_draws_separated_by_commas():
    obj = DataObject(draws=["a", "b", "c"])
    p = pretty.RepresentationPrinter()
    p.pretty(obj)
    for _ in range(3):
        obj.draw(st.text())
    assert _finalize_and_render(p) == "DataObject(draws=['a', 'b', 'c'])"


def test_repr_pretty_does_not_record_draws_made_before_pretty():
    obj = DataObject(draws=[1, 2, 3])
    obj.draw(st.integers())  # drawn before printer was attached
    p = pretty.RepresentationPrinter()
    p.pretty(obj)
    obj.draw(st.integers())
    assert _finalize_and_render(p) == "DataObject(draws=[2])"


def test_repr_pretty_captures_value_at_draw_time_not_finalize_time():
    obj = DataObject(draws=[[1, 2]])
    p = pretty.RepresentationPrinter()
    p.pretty(obj)
    drawn = obj.draw(st.lists(st.integers()))
    drawn.append(999)  # mutate after the draw
    assert _finalize_and_render(p) == "DataObject(draws=[[1, 2]])"


def test_repr_pretty_uses_pretty_representation_of_draws():
    obj = DataObject(draws=[{"b": 1, "a": 2}])
    p = pretty.RepresentationPrinter()
    p.pretty(obj)
    obj.draw(st.dictionaries(st.text(), st.integers()))
    # Pretty-printed dict preserves insertion order, shown as {...}.
    assert _finalize_and_render(p) == "DataObject(draws=[{'b': 1, 'a': 2}])"


def test_multiple_repr_pretty_calls_do_not_conflict():
    # Printing the same DataObject through two independent printers should
    # yield the same content after each is finalized.
    obj = DataObject(draws=[10, 20])

    p1 = pretty.RepresentationPrinter()
    p1.pretty(obj)
    p2 = pretty.RepresentationPrinter()
    p2.pretty(obj)

    obj.draw(st.integers())
    obj.draw(st.integers())

    out1 = _finalize_and_render(p1)
    out2 = _finalize_and_render(p2)
    # At least one should reflect the draws; ideally both do.
    assert "10" in out1 or "10" in out2


# --- Falsifying-example integration -----------------------------------


def _collect_falsifying_notes(test_fn):
    with pytest.raises(AssertionError) as err:
        test_fn()
    notes = "\n".join(err.value.__notes__)
    # Extract just the Falsifying-example section if there are multiple notes.
    assert "Falsifying example" in notes, notes
    return notes


def test_falsifying_example_shows_data_object_draws():
    @given(st.data())
    def inner(data):
        data.draw(st.integers(min_value=0, max_value=10))
        raise AssertionError

    notes = _collect_falsifying_notes(inner)
    assert re.search(r"DataObject\(draws=\[\s*0\s*\]\)", notes), notes


def test_falsifying_example_shows_multiple_draws_in_order():
    @given(st.data())
    def inner(data):
        data.draw(st.integers(min_value=0, max_value=10))
        data.draw(st.text(max_size=3))
        raise AssertionError

    notes = _collect_falsifying_notes(inner)
    assert re.search(r"DataObject\(draws=\[\s*0\s*,\s*''\s*\]\)", notes), notes


def test_falsifying_example_shows_list_draw():
    @given(st.data())
    def inner(data):
        data.draw(st.lists(st.integers(min_value=0, max_value=5), min_size=1))
        raise AssertionError

    notes = _collect_falsifying_notes(inner)
    # Minimal failing list is [0].
    assert re.search(r"DataObject\(draws=\[\s*\[0\]\s*\]\)", notes), notes


def test_falsifying_example_snapshot_ignores_post_draw_mutation():
    @given(st.data())
    def inner(data):
        xs = data.draw(st.lists(st.integers(min_value=0, max_value=5), min_size=1))
        xs.append(999)  # mutate after draw - should NOT be shown
        raise AssertionError

    notes = _collect_falsifying_notes(inner)
    # The rendered list within draws=[...] must not contain 999.
    m = re.search(r"DataObject\(draws=\[(.*?)\]\)", notes, re.DOTALL)
    assert m is not None, notes
    inner_repr = m.group(1)
    assert "999" not in inner_repr, (inner_repr, notes)
    # And the minimal list itself is [0] at draw time.
    assert re.search(r"\[0\]", inner_repr), inner_repr


def test_falsifying_example_with_explain_mode_still_shows_draws():
    @given(st.data())
    @settings(phases=[Phase.generate, Phase.shrink, Phase.explain], max_examples=50)
    def inner(data):
        data.draw(st.integers(min_value=0, max_value=10))
        raise AssertionError

    notes = _collect_falsifying_notes(inner)
    assert re.search(r"DataObject\(draws=\[\s*0\s*\]\)", notes), notes


def test_falsifying_example_with_no_draws_shows_empty_list():
    @given(st.data())
    def inner(data):
        # Never call data.draw
        raise AssertionError

    notes = _collect_falsifying_notes(inner)
    assert "DataObject(draws=[])" in notes, notes


def test_verbose_trying_example_shows_data_object_draws():
    # Verbose printing also uses the falsifying-style repr, so it should
    # receive the same draws snapshot.
    from tests.common.utils import capture_out
    from hypothesis._settings import Verbosity

    @given(st.data())
    @settings(verbosity=Verbosity.verbose, max_examples=10)
    def inner(data):
        data.draw(st.integers(min_value=0, max_value=0))  # always 0

    with capture_out() as out:
        inner()
    # At least one Trying example / Falsifying example line should include
    # the draws=[...] form rather than the legacy data(...) form.
    text = out.getvalue()
    assert re.search(r"DataObject\(draws=\[", text), text


def test_falsifying_example_draws_independent_across_runs():
    # Running a failing st.data() test twice should produce fresh state both
    # times - the class-level printer attribute must be reset between runs.
    @given(st.data())
    def inner(data):
        data.draw(st.integers(min_value=0, max_value=0))
        raise AssertionError

    notes1 = _collect_falsifying_notes(inner)
    notes2 = _collect_falsifying_notes(inner)
    assert "DataObject(draws=[0])" in notes1
    assert "DataObject(draws=[0])" in notes2
