# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

from hypothesis import assume, example, given, strategies as st
from hypothesis.internal.conjecture.datatree import (
    MAX_CHILDREN_EFFECTIVELY_INFINITE,
    all_children,
    compute_max_children,
)
from hypothesis.internal.floats import next_down, next_up
from hypothesis.internal.intervalsets import IntervalSet

from tests.conjecture.common import (
    draw_boolean_kwargs,
    draw_bytes_kwargs,
    draw_float_kwargs,
    draw_integer_kwargs,
    draw_string_kwargs,
    fresh_data,
)


@st.composite
def ir_types_and_kwargs(draw):
    ir_type = draw(st.sampled_from(["integer", "bytes", "float", "string", "boolean"]))
    kwargs_strategy = {
        "integer": draw_integer_kwargs(),
        "bytes": draw_bytes_kwargs(),
        "float": draw_float_kwargs(),
        "string": draw_string_kwargs(),
        "boolean": draw_boolean_kwargs(),
    }[ir_type]
    kwargs = draw(kwargs_strategy)

    return (ir_type, kwargs)


# we max out at 128 bit integers in the *unbounded* case, but someone may
# specify a bound with a larger magnitude. Ensure we calculate max children for
# those cases correctly.
@example(("integer", {"min_value": None, "max_value": -(2**200), "weights": None}))
@example(("integer", {"min_value": 2**200, "max_value": None, "weights": None}))
@example(
    ("integer", {"min_value": -(2**200), "max_value": 2**200, "weights": None})
)
@given(ir_types_and_kwargs())
def test_compute_max_children_is_positive(ir_type_and_kwargs):
    (ir_type, kwargs) = ir_type_and_kwargs
    assert compute_max_children(ir_type, kwargs) >= 0


def test_compute_max_children_integer_zero_weight():
    kwargs = {"min_value": 1, "max_value": 2, "weights": [0, 1]}
    assert compute_max_children("integer", kwargs) == 1

    kwargs = {"min_value": 1, "max_value": 4, "weights": [0, 0.5, 0, 0.5]}
    assert compute_max_children("integer", kwargs) == 2


def test_compute_max_children_string_unbounded_max_size():
    kwargs = {
        "min_size": 0,
        "max_size": None,
        "intervals": IntervalSet.from_string("a"),
    }
    assert compute_max_children("string", kwargs) == MAX_CHILDREN_EFFECTIVELY_INFINITE


def test_compute_max_children_string_empty_intervals():
    kwargs = {"min_size": 0, "max_size": 100, "intervals": IntervalSet.from_string("")}
    # only possibility is the empty string
    assert compute_max_children("string", kwargs) == 1


def test_compute_max_children_string_reasonable_size():
    kwargs = {"min_size": 8, "max_size": 8, "intervals": IntervalSet.from_string("abc")}
    # 3 possibilities for each character, 8 characters, 3 ** 8 possibilities.
    assert compute_max_children("string", kwargs) == 3**8

    kwargs = {
        "min_size": 2,
        "max_size": 8,
        "intervals": IntervalSet.from_string("abcd"),
    }
    assert compute_max_children("string", kwargs) == sum(
        4**k for k in range(2, 8 + 1)
    )


def test_compute_max_children_empty_string():
    kwargs = {"min_size": 0, "max_size": 0, "intervals": IntervalSet.from_string("abc")}
    assert compute_max_children("string", kwargs) == 1


def test_compute_max_children_string_very_large():
    kwargs = {
        "min_size": 0,
        "max_size": 10_000,
        "intervals": IntervalSet.from_string("abcdefg"),
    }
    assert compute_max_children("string", kwargs) == MAX_CHILDREN_EFFECTIVELY_INFINITE


def test_compute_max_children_boolean():
    assert compute_max_children("boolean", {"p": 0.0}) == 1
    assert compute_max_children("boolean", {"p": 1.0}) == 1

    assert compute_max_children("boolean", {"p": 0.5}) == 2
    assert compute_max_children("boolean", {"p": 0.001}) == 2
    assert compute_max_children("boolean", {"p": 0.999}) == 2


@given(st.text(min_size=1, max_size=1), st.integers(0, 100))
def test_draw_string_single_interval_with_equal_bounds(s, n):
    data = fresh_data()
    intervals = IntervalSet.from_string(s)
    assert data.draw_string(intervals, min_size=n, max_size=n) == s * n


@example(("boolean", {"p": 2**-65}))
@example(("boolean", {"p": 1 - 2**-65}))
@example(
    (
        "string",
        {"min_size": 0, "max_size": 0, "intervals": IntervalSet.from_string("abc")},
    )
)
@example(
    ("string", {"min_size": 0, "max_size": 3, "intervals": IntervalSet.from_string("")})
)
@example(
    (
        "string",
        {"min_size": 0, "max_size": 3, "intervals": IntervalSet.from_string("a")},
    )
)
# all combinations of float signs
@example(("float", {"min_value": next_down(-0.0), "max_value": -0.0}))
@example(("float", {"min_value": next_down(-0.0), "max_value": next_up(0.0)}))
@example(("float", {"min_value": 0.0, "max_value": next_up(0.0)}))
@example(("integer", {"min_value": 1, "max_value": 2, "weights": [0, 1]}))
@given(ir_types_and_kwargs())
def test_compute_max_children_and_all_children_agree(ir_type_and_kwargs):
    (ir_type, kwargs) = ir_type_and_kwargs
    max_children = compute_max_children(ir_type, kwargs)

    # avoid slowdowns / OOM when reifying extremely large all_children generators.
    # We also hard cap at MAX_CHILDREN_EFFECTIVELY_INFINITE, because max_children
    # returns approximations after this value and so will disagree with
    # all_children.
    cap = min(100_000, MAX_CHILDREN_EFFECTIVELY_INFINITE)
    assume(max_children < cap)
    assert len(list(all_children(ir_type, kwargs))) == max_children
