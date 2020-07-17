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

import random

from pytest import raises

from hypothesis import Verbosity, find, given, settings, strategies as st
from tests.common.utils import no_shrink


def test_seeds_off_random():
    s = settings(phases=no_shrink, database=None)
    r = random.getstate()
    x = find(st.integers(), lambda x: True, settings=s)
    random.setstate(r)
    y = find(st.integers(), lambda x: True, settings=s)
    assert x == y


def test_nesting_with_control_passes_health_check():
    @given(st.integers(0, 100), st.random_module())
    @settings(max_examples=5, database=None, deadline=None)
    def test_blah(x, rnd):
        @given(st.integers())
        @settings(
            max_examples=100, phases=no_shrink, database=None, verbosity=Verbosity.quiet
        )
        def test_nest(y):
            assert y < x

        with raises(AssertionError):
            test_nest()

    test_blah()
