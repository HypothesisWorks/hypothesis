# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import pytest

from hypothesis import example, given, strategies as st
from hypothesis.errors import StopTest
from hypothesis.internal.compat import WINDOWS
from hypothesis.internal.conjecture.choice import (
    choice_equal,
    choice_from_index,
    choice_permitted,
)
from hypothesis.internal.conjecture.data import ConjectureData
from hypothesis.internal.conjecture.providers import (
    BytestringProvider,
    HypothesisProvider,
    URandomProvider,
)
from hypothesis.internal.intervalsets import IntervalSet

from tests.conjecture.common import (
    choice_types_constraints,
    float_constr,
    integer_constr,
    nodes,
    string_constr,
)


@example(b"\x00" * 100, [("integer", integer_constr())])
@example(b"\x00" * 100, [("integer", integer_constr(0, 2))])
@example(b"\x00" * 100, [("integer", integer_constr(0, 0))])
@example(b"\x00" * 100, [("integer", integer_constr(min_value=0))])
@example(b"\x00" * 100, [("integer", integer_constr(max_value=2))])
@example(b"\x00" * 100, [("integer", integer_constr(0, 2, weights={0: 0.1}))])
@example(b"\x00" * 100, [("boolean", {"p": 1.0})])
@example(b"\x00" * 100, [("boolean", {"p": 0.0})])
@example(b"\x00" * 100, [("boolean", {"p": 1e-99})])
@example(b"\x00" * 100, [("string", string_constr(IntervalSet.from_string("a")))])
@example(b"\x00" * 100, [("float", float_constr())])
@example(b"\x00" * 100, [("bytes", {"min_size": 0, "max_size": 10})])
@example(b"\x00", [("integer", integer_constr())])
@given(st.binary(min_size=200), st.lists(choice_types_constraints()))
def test_provider_contract_bytestring(bytestring, choice_type_and_constraints):
    data = ConjectureData(
        random=None,
        observer=None,
        provider=BytestringProvider,
        provider_kw={"bytestring": bytestring},
    )

    for choice_type, constraints in choice_type_and_constraints:
        try:
            value = getattr(data, f"draw_{choice_type}")(**constraints)
        except StopTest:
            return

        assert choice_permitted(value, constraints)
        constraints["forced"] = choice_from_index(0, choice_type, constraints)
        assert choice_equal(
            constraints["forced"], getattr(data, f"draw_{choice_type}")(**constraints)
        )


@pytest.mark.parametrize(
    "provider",
    [
        pytest.param(
            URandomProvider,
            marks=pytest.mark.skipif(
                WINDOWS, reason="/dev/urandom not available on windows"
            ),
        ),
        HypothesisProvider,
    ],
)
@given(st.lists(nodes()), st.randoms())
def test_provider_contract(provider, nodes, random):
    data = ConjectureData(random=random, provider=provider)
    for node in nodes:
        value = getattr(data, f"draw_{node.type}")(**node.constraints)
        assert choice_permitted(value, node.constraints)
