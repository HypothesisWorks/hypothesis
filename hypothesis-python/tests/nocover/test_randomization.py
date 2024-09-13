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

from hypothesis import Verbosity, core, find, given, settings, strategies as st

from tests.common.utils import no_shrink


def test_seeds_off_internal_random():
    s = settings(phases=no_shrink, database=None)
    r = core._hypothesis_global_random.getstate()
    x = find(st.integers(), lambda x: True, settings=s)
    core._hypothesis_global_random.setstate(r)
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

        with pytest.raises(AssertionError):
            test_nest()

    test_blah()
