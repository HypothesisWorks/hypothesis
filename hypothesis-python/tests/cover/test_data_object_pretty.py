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
    assert _finalize_and_render(p) == (
        "DataObject(draws=[\n"
        "    1,\n"
        "    2,\n"
        "    3,\n"
        "])"
    )


def test_repr_pretty_single_draw():
    obj = DataObject(draws=["hello"])
    p = pretty.RepresentationPrinter()
    p.pretty(obj)
    obj.draw(st.text())
    assert _finalize_and_render(p) == (
        "DataObject(draws=[\n"
        "    'hello',\n"
        "])"
    )


def test_repr_pretty_does_not_record_draws_made_before_pretty():
    obj = DataObject(draws=[1, 2, 3])
    obj.draw(st.integers())  # drawn before printer was attached
    p = pretty.RepresentationPrinter()
    p.pretty(obj)
    obj.draw(st.integers())
    assert _finalize_and_render(p) == (
        "DataObject(draws=[\n"
        "    2,\n"
        "])"
    )


def test_repr_pretty_captures_value_at_draw_time_not_finalize_time():
    obj = DataObject(draws=[[1, 2]])
    p = pretty.RepresentationPrinter()
    p.pretty(obj)
    drawn = obj.draw(st.lists(st.integers()))
    drawn.append(999)  # mutate after the draw
    assert _finalize_and_render(p) == (
        "DataObject(draws=[\n"
        "    [1, 2],\n"
        "])"
    )


def test_repr_pretty_uses_pretty_representation_of_draws():
    obj = DataObject(draws=[{"b": 1, "a": 2}])
    p = pretty.RepresentationPrinter()
    p.pretty(obj)
    obj.draw(st.dictionaries(st.text(), st.integers()))
    assert _finalize_and_render(p) == (
        "DataObject(draws=[\n"
        "    {'b': 1, 'a': 2},\n"
        "])"
    )


# --- Label handling ---------------------------------------------------


def test_labeled_draw_renders_comment_on_preceding_line():
    obj = DataObject(draws=[42])
    p = pretty.RepresentationPrinter()
    p.pretty(obj)
    obj.draw(st.integers(), label="Cool thing")
    assert _finalize_and_render(p) == (
        "DataObject(draws=[\n"
        "    # Cool thing\n"
        "    42,\n"
        "])"
    )


def test_labeled_and_unlabeled_draws_mix_correctly():
    obj = DataObject(draws=[1, 2, 3])
    p = pretty.RepresentationPrinter()
    p.pretty(obj)
    obj.draw(st.integers())
    obj.draw(st.integers(), label="second")
    obj.draw(st.integers())
    assert _finalize_and_render(p) == (
        "DataObject(draws=[\n"
        "    1,\n"
        "    # second\n"
        "    2,\n"
        "    3,\n"
        "])"
    )


def test_label_comment_uses_label_text_verbatim():
    # Labels with spaces, punctuation, etc. pass through as the comment body.
    obj = DataObject(draws=[1])
    p = pretty.RepresentationPrinter()
    p.pretty(obj)
    obj.draw(st.integers(), label="some label: with : colons")
    rendered = _finalize_and_render(p)
    assert "# some label: with : colons" in rendered


# --- Falsifying-example integration -----------------------------------


def _collect_falsifying_notes(test_fn):
    with pytest.raises(AssertionError) as err:
        test_fn()
    notes = "\n".join(err.value.__notes__)
    # Extract just the Falsifying-example section if there are multiple notes.
    assert "Falsifying example" in notes, notes
    return notes


_DRAWS_OPEN = r"DataObject\(draws=\[\s*"
_DRAWS_CLOSE = r"\s*\]\)"


def test_falsifying_example_shows_data_object_draws():
    @given(st.data())
    def inner(data):
        data.draw(st.integers(min_value=0, max_value=10))
        raise AssertionError

    notes = _collect_falsifying_notes(inner)
    assert re.search(_DRAWS_OPEN + r"0,?" + _DRAWS_CLOSE, notes), notes


def test_falsifying_example_shows_multiple_draws_in_order():
    @given(st.data())
    def inner(data):
        data.draw(st.integers(min_value=0, max_value=10))
        data.draw(st.text(max_size=3))
        raise AssertionError

    notes = _collect_falsifying_notes(inner)
    assert re.search(
        _DRAWS_OPEN + r"0\s*,\s*''\s*,?" + _DRAWS_CLOSE, notes
    ), notes


def test_falsifying_example_shows_list_draw():
    @given(st.data())
    def inner(data):
        data.draw(st.lists(st.integers(min_value=0, max_value=5), min_size=1))
        raise AssertionError

    notes = _collect_falsifying_notes(inner)
    # Minimal failing list is [0].
    assert re.search(_DRAWS_OPEN + r"\[0\]\s*,?" + _DRAWS_CLOSE, notes), notes


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
    assert re.search(_DRAWS_OPEN + r"0,?" + _DRAWS_CLOSE, notes), notes


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
    # times.
    @given(st.data())
    def inner(data):
        data.draw(st.integers(min_value=0, max_value=0))
        raise AssertionError

    notes1 = _collect_falsifying_notes(inner)
    notes2 = _collect_falsifying_notes(inner)
    assert re.search(r"DataObject\(draws=\[\s*0\s*,?\s*\]\)", notes1), notes1
    assert re.search(r"DataObject\(draws=\[\s*0\s*,?\s*\]\)", notes2), notes2


def test_falsifying_example_no_longer_emits_draw_note_lines():
    # The per-draw ``Draw N: value`` notes have been replaced by the
    # ``DataObject(draws=[...])`` rendering.
    @given(st.data())
    def inner(data):
        data.draw(st.integers(min_value=0, max_value=10))
        data.draw(st.integers(min_value=0, max_value=10))
        raise AssertionError

    notes = _collect_falsifying_notes(inner)
    assert "Draw 1" not in notes, notes
    assert "Draw 2" not in notes, notes


def test_falsifying_example_shows_label_as_comment():
    @given(st.data())
    def inner(data):
        data.draw(st.integers(min_value=0, max_value=0), label="Cool thing")
        raise AssertionError

    notes = _collect_falsifying_notes(inner)
    assert "# Cool thing" in notes, notes
    # And the label annotates the right draw (appears before the value).
    m = re.search(r"# Cool thing\s*\n\s*0", notes)
    assert m is not None, notes


# --- Snapshot tests ---------------------------------------------------
#
# These pin the exact falsifying-example output for a variety of draw
# scenarios, so that changes to the rendering (indentation, comma
# placement, label formatting, etc.) have to be made deliberately by
# regenerating the snapshot.


def snapshot_given(*strategies, **kwarg_strategies):
    """Decorator that turns the wrapped body into a pytest test: runs it as
    a Hypothesis property test that always fails, and asserts the captured
    falsifying-example output equals the ``snapshot`` fixture value."""
    import functools
    import inspect

    def decorator(body):
        @functools.wraps(body)
        def prop_body(*args, **kwargs):
            body(*args, **kwargs)
            raise AssertionError

        prop_body.__signature__ = inspect.signature(body)
        prop_test = given(*strategies, **kwarg_strategies)(
            settings(print_blob=False, derandomize=True)(prop_body)
        )

        @functools.wraps(body)
        def test_fn(snapshot):
            with pytest.raises(AssertionError) as err:
                prop_test()
            assert "\n".join(err.value.__notes__).strip() == snapshot

        test_fn.__signature__ = inspect.Signature(
            [inspect.Parameter("snapshot", inspect.Parameter.POSITIONAL_OR_KEYWORD)]
        )
        return test_fn

    return decorator


@snapshot_given(st.data())
def test_snapshot_no_draws(data):
    pass


@snapshot_given(st.data())
def test_snapshot_single_draw(data):
    data.draw(st.integers(min_value=0, max_value=10))


@snapshot_given(st.data())
def test_snapshot_multiple_unlabeled_draws(data):
    data.draw(st.integers(min_value=0, max_value=10))
    data.draw(st.text(max_size=3))
    data.draw(st.booleans())


@snapshot_given(st.data())
def test_snapshot_single_labeled_draw(data):
    data.draw(st.integers(min_value=0, max_value=10), label="Cool thing")


@snapshot_given(st.data())
def test_snapshot_all_labeled_draws(data):
    data.draw(st.integers(min_value=0, max_value=10), label="first number")
    data.draw(st.integers(min_value=0, max_value=10), label="second number")


@snapshot_given(st.data())
def test_snapshot_mixed_labeled_and_unlabeled(data):
    data.draw(st.integers(min_value=0, max_value=10))
    data.draw(st.text(max_size=3), label="middle")
    data.draw(st.booleans())


@snapshot_given(st.data())
def test_snapshot_nested_value(data):
    data.draw(
        st.lists(st.integers(min_value=0, max_value=5), min_size=1),
        label="a list",
    )


@snapshot_given(st.integers(min_value=0, max_value=10), st.data())
def test_snapshot_alongside_other_args(n, data):
    data.draw(st.integers(min_value=0, max_value=10), label="inner draw")


@snapshot_given(st.data(), st.data())
def test_snapshot_two_data_args(d1, d2):
    d1.draw(st.integers(min_value=0, max_value=10), label="from d1")
    d2.draw(st.integers(min_value=0, max_value=10))
