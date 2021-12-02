# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Most of this work is copyright (C) 2013-2021 David R. MacIver
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

from sys import float_info

import pytest

from hypothesis.errors import InvalidArgument
from hypothesis.internal.floats import next_down, next_up
from hypothesis.strategies import floats
from hypothesis.strategies._internal.numbers import next_down_normal, next_up_normal

from tests.common.debug import assert_no_examples, find_any
from tests.common.utils import PYTHON_FTZ

pytestmark = [pytest.mark.skipif(PYTHON_FTZ, reason="broken by unsafe compiler flags")]


def kw(marks=(), **kwargs):
    id_ = ", ".join(f"{k}={v!r}" for k, v in kwargs.items())
    return pytest.param(kwargs, id=id_, marks=marks)


@pytest.mark.parametrize(
    "kwargs",
    [
        kw(min_value=1),
        kw(min_value=1),
        kw(max_value=-1),
        kw(min_value=float_info.min),
        kw(min_value=next_down(float_info.min), exclude_min=True),
        kw(max_value=-float_info.min),
        kw(min_value=next_up(-float_info.min), exclude_max=True),
    ],
)
def test_subnormal_validation(kwargs):
    strat = floats(**kwargs, allow_subnormal=True)
    with pytest.raises(InvalidArgument):
        strat.example()


@pytest.mark.parametrize(
    "kwargs",
    [
        # min value
        kw(allow_subnormal=False, min_value=1),
        kw(allow_subnormal=False, min_value=float_info.min),
        kw(allow_subnormal=True, min_value=-1),
        kw(allow_subnormal=True, min_value=next_down(float_info.min)),
        # max value
        kw(allow_subnormal=False, max_value=-1),
        kw(allow_subnormal=False, max_value=-float_info.min),
        kw(allow_subnormal=True, max_value=1),
        kw(allow_subnormal=True, max_value=next_up(-float_info.min)),
        # min/max values
        kw(
            allow_subnormal=True,
            min_value=-1,
            max_value=1,
            marks=pytest.mark.skip(
                reason="FixedBoundFloatStrategy(0, 1) rarely generates subnormals"
            ),
        ),
        kw(
            allow_subnormal=True,
            min_value=next_down(float_info.min),
            max_value=float_info.min,
        ),
        kw(
            allow_subnormal=True,
            min_value=-float_info.min,
            max_value=next_up(-float_info.min),
        ),
        kw(allow_subnormal=False, min_value=-1, max_value=-float_info.min),
        kw(allow_subnormal=False, min_value=float_info.min, max_value=1),
    ],
)
def test_allow_subnormal_defaults_correctly(kwargs):
    allow_subnormal = kwargs.pop("allow_subnormal")
    strat = floats(**kwargs).filter(lambda x: x != 0)
    if allow_subnormal:
        find_any(strat, lambda x: -float_info.min < x < float_info.min)
    else:
        assert_no_examples(strat, lambda x: -float_info.min < x < float_info.min)


@pytest.mark.parametrize(
    "func, val, expected",
    [
        (next_up_normal, -float_info.min, -0.0),
        (next_up_normal, +0.0, float_info.min),
        (next_down_normal, float_info.min, +0.0),
        (next_down_normal, -0.0, -float_info.min),
    ],
)
def test_next_float_normal(func, val, expected):
    assert func(value=val, width=64, allow_subnormal=False) == expected
