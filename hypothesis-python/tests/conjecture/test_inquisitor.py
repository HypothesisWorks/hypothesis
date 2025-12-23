# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import traceback

import pytest

from hypothesis import given, settings, strategies as st

from tests.common.utils import fails_with


def fails_with_output(expected):
    def _inner(f):
        def _new():
            with pytest.raises(AssertionError) as err:
                f()

            if not hasattr(err.value, "__notes__"):
                traceback.print_exception(err.value)
                raise Exception(
                    "err.value does not have __notes__, something has gone "
                    "deeply wrong in the internals"
                )

            got = "\n".join(err.value.__notes__).strip() + "\n"
            assert got == expected.strip() + "\n"

        return _new

    return _inner


@fails_with_output(
    """
Falsifying example: test_inquisitor_comments_basic_fail_if_either(
    # The test always failed when commented parts were varied together.
    a=False,  # or any other generated value
    b=True,
    c=[],  # or any other generated value
    d=True,
    e=False,  # or any other generated value
)
"""
)
@settings(print_blob=False, derandomize=True)
@given(st.booleans(), st.booleans(), st.lists(st.none()), st.booleans(), st.booleans())
def test_inquisitor_comments_basic_fail_if_either(a, b, c, d, e):
    assert not (b and d)


@fails_with_output(
    """
Falsifying example: test_inquisitor_comments_basic_fail_if_not_all(
    # The test sometimes passed when commented parts were varied together.
    a='',  # or any other generated value
    b='',  # or any other generated value
    c='',  # or any other generated value
)
"""
)
@settings(print_blob=False, derandomize=True)
@given(st.text(), st.text(), st.text())
def test_inquisitor_comments_basic_fail_if_not_all(a, b, c):
    condition = a and b and c
    assert condition


@fails_with_output(
    """
Falsifying example: test_inquisitor_no_together_comment_if_single_argument(
    a='',
    b='',  # or any other generated value
)
"""
)
@settings(print_blob=False, derandomize=True)
@given(st.text(), st.text())
def test_inquisitor_no_together_comment_if_single_argument(a, b):
    assert a


@st.composite
def ints_with_forced_draw(draw):
    data = draw(st.data())
    n = draw(st.integers())
    data.conjecture_data.draw_boolean(forced=True)
    return n


@fails_with_output(
    """
Falsifying example: test_inquisitor_doesnt_break_on_varying_forced_nodes(
    n1=100,
    n2=0,  # or any other generated value
)
"""
)
@settings(print_blob=False, derandomize=True)
@given(st.integers(), ints_with_forced_draw())
def test_inquisitor_doesnt_break_on_varying_forced_nodes(n1, n2):
    assert n1 < 100


@fails_with(ZeroDivisionError)
@settings(database=None)
@given(start_date=st.datetimes(), data=st.data())
def test_issue_3755_regression(start_date, data):
    data.draw(st.datetimes(min_value=start_date))
    raise ZeroDivisionError


# Tests for sub-argument explanations


class MyClass:
    def __init__(self, x, y):
        self.x = x
        self.y = y


@fails_with_output(
    """
Falsifying example: test_inquisitor_builds_subargs(
    obj=MyClass(
        0,  # or any other generated value
        True,
    ),
)
"""
)
@settings(print_blob=False, derandomize=True)
@given(st.builds(MyClass, st.integers(), st.booleans()))
def test_inquisitor_builds_subargs(obj):
    assert not obj.y


@fails_with_output(
    """
Falsifying example: test_inquisitor_builds_kwargs_subargs(
    obj=MyClass(
        x=0,  # or any other generated value
        y=True,
    ),
)
"""
)
@settings(print_blob=False, derandomize=True)
@given(st.builds(MyClass, x=st.integers(), y=st.booleans()))
def test_inquisitor_builds_kwargs_subargs(obj):
    assert not obj.y


@fails_with_output(
    """
Falsifying example: test_inquisitor_tuple_subargs(
    t=(
        0,  # or any other generated value
        True,
    ),
)
"""
)
@settings(print_blob=False, derandomize=True)
@given(st.tuples(st.integers(), st.booleans()))
def test_inquisitor_tuple_subargs(t):
    assert not t[1]


@fails_with_output(
    """
Falsifying example: test_inquisitor_fixeddict_subargs(
    d={
        'x': 0,  # or any other generated value
        'y': True,
    },
)
"""
)
@settings(print_blob=False, derandomize=True)
@given(st.fixed_dictionaries({"x": st.integers(), "y": st.booleans()}))
def test_inquisitor_fixeddict_subargs(d):
    assert not d["y"]


@fails_with_output(
    """
Falsifying example: test_inquisitor_tuple_multiple_varying(
    t=(
        0,  # or any other generated value
        '',  # or any other generated value
        True,
    ),
)
"""
)
@settings(print_blob=False, derandomize=True)
@given(st.tuples(st.integers(), st.text(), st.booleans()))
def test_inquisitor_tuple_multiple_varying(t):
    # Multiple sub-arguments can vary, but the "together" comment only applies
    # to top-level test arguments, not to sub-arguments within composites.
    assert not t[2]


@fails_with_output(
    """
Falsifying example: test_inquisitor_skip_subset_slices(
    obj=MyClass(
        (0, False),  # or any other generated value
        y=False,
    ),
)
"""
)
@settings(print_blob=False, derandomize=True)
@given(st.builds(MyClass, st.tuples(st.integers(), st.booleans()), y=st.booleans()))
def test_inquisitor_skip_subset_slices(obj):
    # The tuple can vary freely, but the booleans inside it shouldn't
    # get individual comments since they're part of a larger varying slice.
    assert obj.y


# Test for duplicate param names at different nesting levels
@fails_with_output(
    """
Falsifying example: test_inquisitor_duplicate_param_names(
    kw=0,  # or any other generated value
    b={
        'kw': '',  # or any other generated value
        'c': True,
    },
)
"""
)
@settings(print_blob=False, derandomize=True)
@given(kw=st.integers(), b=st.fixed_dictionaries({"kw": st.text(), "c": st.booleans()}))
def test_inquisitor_duplicate_param_names(kw, b):
    # Both "kw" (top-level) and "b['kw']" can vary - they get separate comments
    # even though they have the same name at different nesting levels.
    # b['c'] is the critical value that determines the failure.
    assert not b["c"]


# Test for multi-level nesting: bare, nested, and double-nested
class Outer:
    def __init__(self, inner, value):
        self.inner = inner
        self.value = value


class Inner:
    def __init__(self, x):
        self.x = x


@fails_with_output(
    """
Falsifying example: test_inquisitor_multi_level_nesting(
    bare=0,  # or any other generated value
    outer=Outer(
        inner=Inner(x=0),  # or any other generated value
        value=True,
    ),
)
"""
)
@settings(print_blob=False, derandomize=True)
@given(
    bare=st.integers(),
    outer=st.builds(
        Outer, inner=st.builds(Inner, x=st.integers()), value=st.booleans()
    ),
)
def test_inquisitor_multi_level_nesting(bare, outer):
    # Comments on: bare (top-level) and outer.inner (nested). The inner.x slice
    # is the same as inner's slice since Inner has only one argument, so the
    # comment appears only once on inner. outer.value doesn't get a comment
    # because it's the critical value that determines the failure.
    assert not outer.value
