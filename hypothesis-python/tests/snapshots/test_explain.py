# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

from hypothesis import given, strategies as st

from tests.common.utils import (
    EXPLAIN_SETTINGS,
    run_test_for_falsifying_example,
    snapshot_given,
)


def test_explain_comments_basic_fail_if_either(snapshot):
    @EXPLAIN_SETTINGS
    @given(
        st.booleans(),
        st.booleans(),
        st.lists(st.none()),
        st.booleans(),
        st.booleans(),
    )
    def inner(a, b, c, d, e):
        assert not (b and d)

    assert run_test_for_falsifying_example(inner) == snapshot


def test_explain_comments_basic_fail_if_not_all(snapshot):
    @EXPLAIN_SETTINGS
    @given(st.text(), st.text(), st.text())
    def inner(a, b, c):
        condition = a and b and c
        assert condition

    assert run_test_for_falsifying_example(inner) == snapshot


def test_explain_no_together_comment_if_single_argument(snapshot):
    @EXPLAIN_SETTINGS
    @given(st.text(), st.text())
    def inner(a, b):
        assert a

    assert run_test_for_falsifying_example(inner) == snapshot


class MyClass:
    def __init__(self, x, y):
        self.x = x
        self.y = y


def test_explain_builds_subargs(snapshot):
    @EXPLAIN_SETTINGS
    @given(st.builds(MyClass, st.integers(), st.booleans()))
    def inner(obj):
        assert not obj.y

    assert run_test_for_falsifying_example(inner) == snapshot


def test_explain_builds_kwargs_subargs(snapshot):
    @EXPLAIN_SETTINGS
    @given(st.builds(MyClass, x=st.integers(), y=st.booleans()))
    def inner(obj):
        assert not obj.y

    assert run_test_for_falsifying_example(inner) == snapshot


def test_explain_tuple_subargs(snapshot):
    @EXPLAIN_SETTINGS
    @given(st.tuples(st.integers(), st.booleans()))
    def inner(t):
        assert not t[1]

    assert run_test_for_falsifying_example(inner) == snapshot


def test_explain_fixeddict_subargs(snapshot):
    @EXPLAIN_SETTINGS
    @given(st.fixed_dictionaries({"x": st.integers(), "y": st.booleans()}))
    def inner(d):
        assert not d["y"]

    assert run_test_for_falsifying_example(inner) == snapshot


def test_explain_tuple_multiple_varying(snapshot):
    @EXPLAIN_SETTINGS
    @given(st.tuples(st.integers(), st.text(), st.booleans()))
    def inner(t):
        assert not t[2]

    assert run_test_for_falsifying_example(inner) == snapshot


def test_explain_skip_subset_slices(snapshot):
    @EXPLAIN_SETTINGS
    @given(st.builds(MyClass, st.tuples(st.integers(), st.booleans()), y=st.booleans()))
    def inner(obj):
        assert obj.y

    assert run_test_for_falsifying_example(inner) == snapshot


def test_explain_duplicate_param_names(snapshot):
    @EXPLAIN_SETTINGS
    @given(
        kw=st.integers(),
        b=st.fixed_dictionaries({"kw": st.text(), "c": st.booleans()}),
    )
    def inner(kw, b):
        assert not b["c"]

    assert run_test_for_falsifying_example(inner) == snapshot


class Outer:
    def __init__(self, inner, value):
        self.inner = inner
        self.value = value


class Inner:
    def __init__(self, x):
        self.x = x


def test_explain_multi_level_nesting(snapshot):
    @EXPLAIN_SETTINGS
    @given(
        bare=st.integers(),
        outer=st.builds(
            Outer, inner=st.builds(Inner, x=st.integers()), value=st.booleans()
        ),
    )
    def inner(bare, outer):
        assert not outer.value

    assert run_test_for_falsifying_example(inner) == snapshot


@snapshot_given(st.integers(), st.integers())
def test_integers_equal(n1, n2):
    assert n1 == n2


@snapshot_given(st.integers(), st.integers())
def test_integers_less(n1, n2):
    assert n1 < n2


@snapshot_given(st.integers(), st.integers())
def test_integers_greater(n1, n2):
    assert n1 < n2
