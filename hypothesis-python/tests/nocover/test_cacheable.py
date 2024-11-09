# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import gc
import weakref

import pytest

from hypothesis import given, settings, strategies as st


@pytest.mark.parametrize(
    "s",
    [
        st.floats(),
        st.tuples(st.integers()),
        st.tuples(),
        st.one_of(st.integers(), st.text()),
    ],
)
def test_is_cacheable(s):
    assert s.is_cacheable


@pytest.mark.parametrize(
    "s",
    [
        st.just([]),
        st.tuples(st.integers(), st.just([])),
        st.one_of(st.integers(), st.text(), st.just([])),
    ],
)
def test_is_not_cacheable(s):
    assert not s.is_cacheable


def test_non_cacheable_things_are_not_cached():
    x = st.just([])
    assert st.tuples(x) != st.tuples(x)


def test_cacheable_things_are_cached():
    x = st.just(())
    assert st.tuples(x) == st.tuples(x)


def test_local_types_are_garbage_collected_issue_493():
    store = None

    def run_locally():
        class Test:
            @settings(database=None)
            @given(st.integers())
            def test(self, i):
                pass

        nonlocal store
        store = weakref.ref(Test)
        Test().test()

    run_locally()
    del run_locally
    assert store() is not None
    gc.collect()
    assert store() is None
