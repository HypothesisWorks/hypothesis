# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

from hypothesis import example, given, strategies as st
from hypothesis.internal.conjecture.datatree import compute_max_children
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
@example(("integer", {"min_value": None, "max_value": -(2**200)}))
@example(("integer", {"min_value": 2**200, "max_value": None}))
@example(("integer", {"min_value": -(2**200), "max_value": 2**200}))
@given(ir_types_and_kwargs())
def test_compute_max_children_is_positive(ir_type_and_kwargs):
    (ir_type, kwargs) = ir_type_and_kwargs
    assert compute_max_children(kwargs, ir_type) >= 0


@given(st.text(min_size=1, max_size=1), st.integers(0, 100))
def test_draw_string_single_interval_with_equal_bounds(s, n):
    data = fresh_data()
    intervals = IntervalSet.from_string(s)
    assert data.draw_string(intervals, min_size=n, max_size=n) == s * n
