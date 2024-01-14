# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

from hypothesis import example, given
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


def _test_empty_range(ir_type, kwargs):
    """
    Tests that if we only have a single choice for an ir node, that choice is
    never written to the bitstream, and vice versa. In other words, we write to
    the bitstream iff there were multiple valid choices to begin with.

    This possibility is present in almost every ir node:
    1. draw_integer(n, n)
    2. draw_bytes(0)
    3. draw_float(n, n)
    4. draw_string(max_size=0)
    5. draw_boolean(p=0)

    """
    data = fresh_data()
    draw_func = getattr(data, f"draw_{ir_type}")
    draw_func(**kwargs)

    empty_buffer = data.buffer == b""
    single_choice = compute_max_children(kwargs, ir_type) == 1
    # empty_buffer iff single_choice
    assert empty_buffer and single_choice or (not empty_buffer and not single_choice)


@example({"min_value": 0, "max_value": 0})
@given(draw_integer_kwargs())
def test_empty_range_integer(kwargs):
    _test_empty_range("integer", kwargs)


@example({"size": 0})
@given(draw_bytes_kwargs())
def test_empty_range_bytes(kwargs):
    _test_empty_range("bytes", kwargs)


@example({"min_value": 0, "max_value": 0})
@example({"min_value": -0, "max_value": +0})
@given(draw_float_kwargs())
def test_empty_range_float(kwargs):
    _test_empty_range("float", kwargs)


@example({"min_size": 0, "max_size": 0, "intervals": IntervalSet.from_string("abcd")})
@example({"min_size": 42, "max_size": 42, "intervals": IntervalSet.from_string("a")})
@example({"min_size": 0, "max_size": 5, "intervals": IntervalSet.from_string("")})
@given(draw_string_kwargs())
def test_empty_range_string(kwargs):
    _test_empty_range("string", kwargs)


@example({"p": 0})
@given(draw_boolean_kwargs())
def test_empty_range_boolean(kwargs):
    _test_empty_range("boolean", kwargs)
