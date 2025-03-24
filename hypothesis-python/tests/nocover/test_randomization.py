# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

from random import Random

import pytest

from hypothesis import (
    HealthCheck,
    Verbosity,
    core,
    given,
    settings,
    strategies as st,
)

from tests.common.utils import Why, no_shrink, xfail_on_crosshair


@pytest.mark.skipif(
    settings._current_profile == "crosshair",
    reason="we do not yet pass backends the global random seed, so they are not deterministic",
)
def test_seeds_off_internal_random():
    choices1 = []
    choices2 = []

    @given(st.integers())
    def f1(n):
        choices1.append(n)

    @given(st.integers())
    def f2(n):
        choices2.append(n)

    core._hypothesis_global_random = Random(0)
    state = core._hypothesis_global_random.getstate()
    f1()

    core._hypothesis_global_random.setstate(state)
    f2()

    assert choices1 == choices2


@xfail_on_crosshair(Why.nested_given)
def test_nesting_with_control_passes_health_check():
    @given(st.integers(0, 100), st.random_module())
    @settings(
        max_examples=5,
        database=None,
        deadline=None,
        suppress_health_check=[HealthCheck.nested_given],
    )
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
