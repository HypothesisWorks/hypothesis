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

import typing

import pytest

from hypothesis import given, strategies as st
from hypothesis.internal.compat import PYPY


class TreeForwardRefs(typing.NamedTuple):
    val: int
    l: typing.Optional["TreeForwardRefs"]
    r: typing.Optional["TreeForwardRefs"]


@pytest.mark.skipif(PYPY, reason="pypy36 does not resolve the forward refs")
@given(st.builds(TreeForwardRefs))
def test_resolves_forward_references_outside_annotations(t):
    assert isinstance(t, TreeForwardRefs)
