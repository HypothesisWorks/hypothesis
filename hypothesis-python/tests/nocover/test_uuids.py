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

import pytest

from hypothesis import given, strategies as st
from tests.common.debug import minimal


@given(st.lists(st.uuids()))
def test_are_unique(ls):
    assert len(set(ls)) == len(ls)


def test_retains_uniqueness_in_simplify():
    ts = minimal(st.lists(st.uuids()), lambda x: len(x) >= 5)
    assert len(ts) == len(set(ts)) == 5


@pytest.mark.parametrize("version", (1, 2, 3, 4, 5))
def test_can_generate_specified_version(version):
    @given(st.uuids(version=version))
    def inner(uuid):
        assert version == uuid.version

    inner()
