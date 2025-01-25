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
from hypothesis.errors import StopTest
from hypothesis.internal.conjecture.choice import (
    choice_equal,
    choice_from_index,
    choice_permitted,
)
from hypothesis.internal.conjecture.data import ConjectureData
from hypothesis.internal.conjecture.providers import BytestringProvider
from hypothesis.internal.intervalsets import IntervalSet

from tests.conjecture.common import float_kw, integer_kw, ir_types_and_kwargs, string_kw


@example(b"\x00" * 100, [("integer", integer_kw())])
@example(b"\x00" * 100, [("integer", integer_kw(0, 2))])
@example(b"\x00" * 100, [("integer", integer_kw(0, 0))])
@example(b"\x00" * 100, [("integer", integer_kw(min_value=0))])
@example(b"\x00" * 100, [("integer", integer_kw(max_value=2))])
@example(b"\x00" * 100, [("integer", integer_kw(0, 2, weights={0: 0.1}))])
@example(b"\x00" * 100, [("boolean", {"p": 1.0})])
@example(b"\x00" * 100, [("boolean", {"p": 0.0})])
@example(b"\x00" * 100, [("boolean", {"p": 1e-99})])
@example(b"\x00" * 100, [("string", string_kw(IntervalSet.from_string("a")))])
@example(b"\x00" * 100, [("float", float_kw())])
@example(b"\x00" * 100, [("bytes", {"min_size": 0, "max_size": 10})])
@given(st.binary(min_size=200), st.lists(ir_types_and_kwargs()))
def test_provider_contract_bytestring(bytestring, ir_type_and_kwargs):
    data = ConjectureData(
        random=None,
        observer=None,
        provider=BytestringProvider,
        provider_kw={"bytestring": bytestring},
    )

    for ir_type, kwargs in ir_type_and_kwargs:
        try:
            value = getattr(data, f"draw_{ir_type}")(**kwargs)
        except StopTest:
            return

        # ir_value_permitted is currently restricted to what *could* be generated
        # by the buffer. once we're fully on the TCS, we can drop this restriction.
        # until then, the BytestringProvider can theoretically generate values
        # that aren't forcable to a buffer - but this requires an enormous shrink_towards
        # value and is such an edge case that I'm just going to bank on nobody hitting
        # it before we're off the bytestring.
        integer_edge_case = (
            ir_type == "integer"
            and kwargs["shrink_towards"] is not None
            and kwargs["shrink_towards"].bit_length() > 100
        )
        assert choice_permitted(value, kwargs) or integer_edge_case

        kwargs["forced"] = choice_from_index(0, ir_type, kwargs)
        assert choice_equal(
            kwargs["forced"], getattr(data, f"draw_{ir_type}")(**kwargs)
        )
