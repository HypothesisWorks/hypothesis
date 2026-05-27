# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

from hypothesis import HealthCheck, Verbosity, assume, given, settings, strategies as st


@settings(max_examples=1, database=None)
@given(st.integers())
def test_single_example(n):
    pass


@settings(
    max_examples=1,
    database=None,
    suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow],
    verbosity=Verbosity.debug,
)
@given(st.integers())
def test_hard_to_find_single_example(n):
    # Numbers are arbitrary, just deliberately unlikely to hit this too soon.
    assume(n % 50 == 11)
