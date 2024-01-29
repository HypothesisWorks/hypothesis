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

from hypothesis import strategies as st
from hypothesis.errors import InvalidArgument

from tests.common.debug import assert_no_examples, check_can_generate_examples, find_any


def test_no_nil_uuid_by_default():
    assert_no_examples(st.uuids(), lambda x: x == uuid.UUID(int=0))


def test_can_generate_nil_uuid():
    find_any(st.uuids(allow_nil=True), lambda x: x == uuid.UUID(int=0))


def test_can_only_allow_nil_uuid_with_none_version():
    check_can_generate_examples(st.uuids(version=None, allow_nil=True))
    with pytest.raises(InvalidArgument):
        check_can_generate_examples(st.uuids(version=4, allow_nil=True))
    with pytest.raises(InvalidArgument):
        check_can_generate_examples(st.uuids(version=None, allow_nil="not a bool"))
