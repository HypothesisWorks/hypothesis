# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

from pytest import raises

from hypothesis import HealthCheck, Verbosity, given, settings, strategies as st

from tests.common.utils import Why, no_shrink, xfail_on_crosshair


@xfail_on_crosshair(Why.nested_given)
def test_nesting_1():
    @given(st.integers(0, 100))
    @settings(
        max_examples=5,
        database=None,
        deadline=None,
        suppress_health_check=[HealthCheck.nested_given],
    )
    def test_blah(x):
        @given(st.integers())
        @settings(
            max_examples=100, phases=no_shrink, database=None, verbosity=Verbosity.quiet
        )
        def test_nest(y):
            if y >= x:
                raise ValueError

        with raises(ValueError):
            test_nest()

    test_blah()
