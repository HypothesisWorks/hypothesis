# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Most of this work is copyright (C) 2013-2020 David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
# CONTRIBUTING.rst for a full list of people who may hold copyright, and
# consult the git log if you need to determine who owns an individual
# contribution.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.
#
# END HEADER

from inspect import signature
from typing import get_type_hints

from hypothesis import given, strategies as st


def use_this_signature(self, a: int, b: bool = None, *, x: float, y: str):
    pass


class Model:
    # Emulates the implementation of Pydantic models.  See e.g.
    # https://github.com/timothycrosley/hypothesis-auto/issues/10
    __annotations__ = get_type_hints(use_this_signature)
    __signature__ = signature(use_this_signature)

    def __init__(self, **kwargs):
        # Check that we're being called with the expected arguments
        assert set(kwargs) == {"a", "x", "y"}
        assert isinstance(kwargs["a"], int)
        assert isinstance(kwargs["x"], float)
        assert isinstance(kwargs["y"], str)


@given(st.builds(Model))
def test_builds_uses_signature_attribute(val):
    assert isinstance(val, Model)


@given(st.from_type(Model))
def test_from_type_uses_signature_attribute(val):
    assert isinstance(val, Model)
