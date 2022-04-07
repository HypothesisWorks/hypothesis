# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

from __future__ import annotations

from typing import TypedDict, Union

from hypothesis import given, strategies as st


@given(st.data())
def test_complex_forward_ref_in_typed_dict(data):
    alias = Union[int, bool]

    class A(TypedDict):
        a: int

    class B(TypedDict):
        a: A
        b: alias

    b_strategy = st.from_type(B)
    d = data.draw(b_strategy)
    assert isinstance(d["a"], dict)
    assert isinstance(d["a"]["a"], int)
    assert isinstance(d["b"], (int, bool))
