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

import pytest

from hypothesis import given, strategies as st
from hypothesis.errors import InvalidArgument

from tests.common.debug import check_can_generate_examples

alias = Union[int, str]


class A(TypedDict):
    a: int


class B(TypedDict):
    a: A
    b: alias


@given(st.from_type(B))
def test_complex_forward_ref_in_typed_dict(d):
    assert isinstance(d["a"], dict)
    assert isinstance(d["a"]["a"], int)
    assert isinstance(d["b"], (int, str))


def test_complex_forward_ref_in_typed_dict_local():
    local_alias = Union[int, str]

    class C(TypedDict):
        a: A
        b: local_alias

    c_strategy = st.from_type(C)
    with pytest.raises(InvalidArgument):
        check_can_generate_examples(c_strategy)
