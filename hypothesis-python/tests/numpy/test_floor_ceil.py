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

import numpy as np
import pytest

from hypothesis.internal.compat import ceil, floor


@pytest.mark.parametrize(
    "value",
    [
        # These are strings so that the test names are easier to read.
        "2**64+1",
        "2**64-1",
        "2**63+1",
        "2**53+1",
        "-2**53-1",
        "-2**63+1",
        "-2**63-1",
        "-2**64+1",
        "-2**64-1",
    ],
)
def test_our_floor_and_ceil_avoid_numpy_rounding(value):
    a = np.array([eval(value)])

    f = floor(a)
    c = ceil(a)

    assert isinstance(f, int)
    assert isinstance(c, int)

    # Using math.floor or math.ceil for these values would give an incorrect
    # result.
    assert (math.floor(a) > a) or (math.ceil(a) < a)

    assert f <= a <= c
    assert f + 1 > a > c - 1
