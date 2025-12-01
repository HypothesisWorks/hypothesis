# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

from typing import Dict as _Dict, Union

import pytest

from hypothesis import given, settings, strategies as st
from hypothesis.errors import ResolutionFailed

from tests.common.debug import find_any
from tests.common.utils import skipif_threading

# error only occurs with typing variants
# ruff: noqa: UP006, UP035, UP007

# Mutually-recursive types
# See https://github.com/HypothesisWorks/hypothesis/issues/2722

pytestmark = pytest.mark.skipif(
    settings.get_current_profile_name() == "crosshair",
    reason="slow with recursive strustures: https://github.com/pschanely/hypothesis-crosshair/issues/27",
)


# Self-referential recursive forward references
# See https://github.com/HypothesisWorks/hypothesis/issues/4542


def test_self_referential_forward_ref():
    # The example from issue #4542 - a type alias that references itself
    A = list[Union["A", str]]
    # This should work without needing manual registration
    result = find_any(st.from_type(A))
    assert isinstance(result, list)


def test_self_referential_forward_ref_nested():
    # Test with nested self-reference
    Tree = dict[str, Union["Tree", int]]
    result = find_any(st.from_type(Tree))
    assert isinstance(result, dict)


@skipif_threading  # weird errors around b_strategy scope?
@given(st.data())
def test_mutually_recursive_types_with_typevar(data):
    # The previously-failing example from issue #2722
    # Now works because forward refs are resolved via caller namespace lookup
    A = _Dict[bool, "B"]
    B = Union[list[bool], A]

    # Both A and B are in scope, so forward refs should resolve
    data.draw(st.from_type(A))
    data.draw(st.from_type(B))


@skipif_threading  # weird errors around d_strategy scope?
@given(st.data())
def test_mutually_recursive_types_with_typevar_alternate(data):
    # It's not particularly clear why this version passed when the previous
    # test failed, but different behaviour means we add both to the suite.
    C = Union[list[bool], "D"]
    D = dict[bool, C]

    # Both C and D are in scope, so forward refs should resolve
    data.draw(st.from_type(C))
    data.draw(st.from_type(D))


def test_forward_ref_to_undefined_still_fails():
    # Forward references to undefined names should still fail
    A = _Dict[bool, "UndefinedType"]  # noqa: F821

    with pytest.raises(ResolutionFailed, match=r"Could not resolve"):
        find_any(st.from_type(A))
