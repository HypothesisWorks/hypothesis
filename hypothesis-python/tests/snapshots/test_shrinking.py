# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

from hypothesis import given, strategies as st

from tests.snapshots.conftest import SNAPSHOT_SETTINGS


def test_shrunk_list(snapshot, get_output):
    @SNAPSHOT_SETTINGS
    @given(xs=st.lists(st.integers(), min_size=1))
    def inner(xs):
        assert sum(xs) <= 1000

    assert get_output(inner) == snapshot


def test_shrunk_string(snapshot, get_output):
    @SNAPSHOT_SETTINGS
    @given(s=st.text(min_size=1))
    def inner(s):
        assert s == s.lower()

    assert get_output(inner) == snapshot


def test_shrunk_float(snapshot, get_output):
    @SNAPSHOT_SETTINGS
    @given(x=st.floats(min_value=0, max_value=1))
    def inner(x):
        assert x <= 0.5

    assert get_output(inner) == snapshot
