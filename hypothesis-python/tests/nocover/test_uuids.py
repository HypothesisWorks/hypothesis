# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import uuid

import pytest

from hypothesis import given, strategies as st
from hypothesis.errors import InvalidArgument

from tests.common.debug import assert_no_examples, minimal


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


def test_no_nil_uuid():
    assert_no_examples(st.uuids(), lambda x: x == uuid.UUID(int=0))


def test_nil_uuid():
    st.uuids(allow_nil=True), lambda x: x == uuid.UUID(int=0)


def test_can_only_allow_nil_uuid_with_none_version():
    st.uuids(version=None, allow_nil=True).example()
    with pytest.raises(InvalidArgument):
        st.uuids(version=4, allow_nil=True).example()
