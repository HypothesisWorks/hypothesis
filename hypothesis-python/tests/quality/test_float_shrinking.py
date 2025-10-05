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

from hypothesis import HealthCheck, example, given, settings, strategies as st
from hypothesis.internal.compat import ceil

from tests.common.debug import minimal


def test_shrinks_to_simple_floats():
    assert minimal(st.floats(), lambda x: x > 1) == 2.0
    assert minimal(st.floats(), lambda x: x > 0) == 1.0


@pytest.mark.parametrize("n", [1, 2, 3, 8, 10])
def test_can_shrink_in_variable_sized_context(n):
    x = minimal(st.lists(st.floats(), min_size=n), any)
    assert len(x) == n
    assert x.count(0.0) == n - 1
    assert 1 in x


@example(1.7976931348623157e308)
@example(1.5)
@given(st.floats(min_value=0, allow_infinity=False, allow_nan=False))
@settings(suppress_health_check=[HealthCheck.nested_given])
def test_shrinks_downwards_to_integers(f):
    assert minimal(st.floats(min_value=f)) == ceil(f)


@example(1)
@given(st.integers(1, 2**16 - 1))
@settings(suppress_health_check=[HealthCheck.nested_given])
def test_shrinks_downwards_to_integers_when_fractional(b):
    g = minimal(
        st.floats(
            min_value=b, max_value=2**53, exclude_min=True, exclude_max=True
        ).filter(lambda x: int(x) != x)
    )
    assert g == b + 0.5
