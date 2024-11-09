# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

from typing import Dict as _Dict, ForwardRef, Union

import pytest

from hypothesis import given, strategies as st
from hypothesis.errors import ResolutionFailed

from tests.common import utils

# Mutually-recursive types
# See https://github.com/HypothesisWorks/hypothesis/issues/2722


@given(st.data())
def test_mutually_recursive_types_with_typevar(data):
    # The previously-failing example from the issue
    A = _Dict[bool, "B"]
    B = Union[list[bool], A]

    with pytest.raises(ResolutionFailed, match=r"Could not resolve ForwardRef\('B'\)"):
        data.draw(st.from_type(A))

    with utils.temp_registered(
        ForwardRef("B"),
        lambda _: st.deferred(lambda: b_strategy),
    ):
        b_strategy = st.from_type(B)
        data.draw(b_strategy)
        data.draw(st.from_type(A))
        data.draw(st.from_type(B))


@given(st.data())
def test_mutually_recursive_types_with_typevar_alternate(data):
    # It's not particularly clear why this version passed when the previous
    # test failed, but different behaviour means we add both to the suite.
    C = Union[list[bool], "D"]
    D = dict[bool, C]

    with pytest.raises(ResolutionFailed, match=r"Could not resolve ForwardRef\('D'\)"):
        data.draw(st.from_type(C))

    with utils.temp_registered(
        ForwardRef("D"),
        lambda _: st.deferred(lambda: d_strategy),
    ):
        d_strategy = st.from_type(D)
        data.draw(d_strategy)
        data.draw(st.from_type(C))
        data.draw(st.from_type(D))
