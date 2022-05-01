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
