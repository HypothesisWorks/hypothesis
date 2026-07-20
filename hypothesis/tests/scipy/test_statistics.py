# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import math

import pytest
import scipy
import scipy.special

from hypothesis import given, strategies as st
from hypothesis.internal.statistics import stdtr, stdtrit

# Older scipy had a less accurate stdrit path. Our CI uses older scipy in some of our
# older python jobs like python3.10. Just skip them and only test against newer scipy.
SCIPY_VERSION = tuple(int(x) for x in scipy.__version__.split("."))


@given(st.integers(1, 100), st.floats(-1e150, 1e150))
def test_stdtr_matches_scipy(df, t):
    if df == 1:
        # scipy 1.17 regressed the accuracy of stdtr for df=1 at small |t|,
        # with up to ~2e-9 absolute error around t=1e-8 (an upstream issue;
        # df >= 2 still agrees with us to one ulp). df=1 has an exact closed
        # form, so test against that stronger oracle instead of scipy.
        expected = 0.5 + math.atan(t) / math.pi
    else:
        expected = scipy.special.stdtr(df, t)
    assert stdtr(df, t) == pytest.approx(expected, rel=1e-12, abs=1e-15)


@pytest.mark.parametrize("df", [1, 2, 3, 4, 10, 100])
@pytest.mark.parametrize("t", [-100.0, -1.0, -0.5, 0.0, 0.5, 1.0, 100.0])
def test_stdtr_explicit(df, t):
    assert stdtr(df, t) == pytest.approx(
        scipy.special.stdtr(df, t), rel=1e-12, abs=1e-15
    )


# note we split our tests for stdtrit in two:
# * a very aggressive tolerance test for df = 1, 2
# * a less aggressive tolerance test for df > 2
#
# The first test is what we currently care most about, because we use only df=2 in production.
# The second test is currently a sanity check, which is why we're okay with a laxer tolerance.
#
# If we ever change our df use in production, we should revisit these tests and tolerances
# accordingly.
@pytest.mark.skipif(
    SCIPY_VERSION < (1, 17), reason="older scipy has inaccurate stdtrit"
)
@given(st.sampled_from([1, 2]), st.floats(1e-300, 1 - 1e-15))
def test_stdtrit_matches_scipy_strict(df, p):
    # df ∈ {1, 2} use the same closed-form formulas Boost/scipy use, so we
    # expect bit-for-bit (or last-ULP) agreement across the entire p domain.
    assert stdtrit(df, p) == pytest.approx(scipy.special.stdtrit(df, p), rel=1e-15)


@given(st.integers(1, 100), st.floats(1e-9, 1 - 1e-9))
def test_stdtrit_matches_scipy_lax(df, p):
    # df ∈ {1, 2} use closed-form quantiles (last-ULP). df >= 3 uses
    # Newton-on-stdtr instead of scipy's Halley-on-ibeta.
    assert stdtrit(df, p) == pytest.approx(
        scipy.special.stdtrit(df, p), rel=1e-7, abs=1e-9
    )
