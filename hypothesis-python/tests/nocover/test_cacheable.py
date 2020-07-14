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
    store = [None]

    def run_locally():
        class Test:
            @settings(database=None)
            @given(st.integers())
            def test(self, i):
                pass

        store[0] = weakref.ref(Test)
        Test().test()

    run_locally()
    del run_locally
    assert store[0]() is not None
    gc.collect()
    assert store[0]() is None
