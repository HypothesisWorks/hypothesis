# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

from hypothesis import given, settings, strategies as st


def test_biases_towards_boundary_values():
    trillion = 10**12
    boundary_vals = {-trillion, -trillion + 1, trillion - 1, trillion}

    @given(st.integers(-trillion, trillion))
    @settings(max_examples=1000)
    def f(n):
        boundary_vals.discard(n)

    f()

    assert (
        not boundary_vals
    ), f"Expected to see all boundary vals, but still have {boundary_vals}"
