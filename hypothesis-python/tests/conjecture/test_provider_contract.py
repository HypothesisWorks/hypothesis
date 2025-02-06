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

from tests.conjecture.common import (
    choice_types_kwargs,
    float_kw,
    integer_kw,
    nodes,
    string_kw,
)


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
@example(b"\x00", [("integer", integer_kw())])
@given(st.binary(min_size=200), st.lists(choice_types_kwargs()))
def test_provider_contract_bytestring(bytestring, choice_type_and_kwargs):
    data = ConjectureData(
        random=None,
        observer=None,
        provider=BytestringProvider,
        provider_kw={"bytestring": bytestring},
    )

    for choice_type, kwargs in choice_type_and_kwargs:
        try:
            value = getattr(data, f"draw_{choice_type}")(**kwargs)
        except StopTest:
            return

        assert choice_permitted(value, kwargs)
        kwargs["forced"] = choice_from_index(0, choice_type, kwargs)
        assert choice_equal(
            kwargs["forced"], getattr(data, f"draw_{choice_type}")(**kwargs)
        )


@given(st.lists(nodes()), st.randoms())
def test_provider_contract_hypothesis(nodes, random):
    data = ConjectureData(random=random)
    for node in nodes:
        value = getattr(data, f"draw_{node.type}")(**node.kwargs)
        assert choice_permitted(value, node.kwargs)
