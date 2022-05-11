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
from sys import float_info

import pytest

from hypothesis.internal.floats import (
    count_between_floats,
    make_float_clamper,
    next_down,
    next_up,
)


def test_can_handle_straddling_zero():
    assert count_between_floats(-0.0, 0.0) == 2


@pytest.mark.parametrize(
    "func,val",
    [
        (next_up, math.nan),
        (next_up, math.inf),
        (next_up, -0.0),
        (next_down, math.nan),
        (next_down, -math.inf),
        (next_down, 0.0),
    ],
)
def test_next_float_equal(func, val):
    if math.isnan(val):
        assert math.isnan(func(val))
    else:
        assert func(val) == val


@pytest.mark.parametrize(
    "minfloat,maxfloat",
    [
        (0.1, 5.0),
        (0.0, math.inf),
        (0.0, 3.14),
        (100.0, 100.0002),
        (0.9, math.inf),
    ],
)
def test_float_clamper(minfloat, maxfloat):
    clamper = make_float_clamper(minfloat, maxfloat)

    assert clamper(minfloat) == minfloat
    assert clamper(maxfloat) == maxfloat

    inside = next_up(minfloat)
    assert clamper(inside) == inside

    assert minfloat <= clamper(0.0) <= maxfloat
    assert minfloat <= clamper(float_info.min) <= maxfloat
    assert minfloat <= clamper(0.001) <= maxfloat
    assert minfloat <= clamper(1.0) <= maxfloat
    assert minfloat <= clamper(3.14) <= maxfloat
    assert minfloat <= clamper(100.0001) <= maxfloat
    assert minfloat <= clamper(float_info.max) <= maxfloat
    assert minfloat <= clamper(math.inf) <= maxfloat
