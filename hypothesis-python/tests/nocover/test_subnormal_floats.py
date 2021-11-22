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

import math
from sys import float_info

import pytest
from tests.common.debug import assert_all_examples, assert_no_examples, find_any

from hypothesis.errors import InvalidArgument
from hypothesis.internal.floats import next_down, next_up
from hypothesis.strategies import floats

# Tests whether we can represent subnormal floating point numbers.
# IEE-754 requires subnormal support, but it's often disabled anyway by unsafe
# compiler options like `-ffast-math`.  On most hardware that's even a global
# config option, so *linking against* something built this way can break us.
# Everything is terrible
FLUSH_SUBNORMALS_TO_ZERO = next_down(float_info.min) == 0.0


pytestmark = [
    pytest.mark.skipif(
        FLUSH_SUBNORMALS_TO_ZERO, reason="broken by unsafe compiler flags"
    )
]


def test_compiled_with_sane_math_options():
    # Checks that we're not unexpectedly skipping the subnormal tests below.
    assert not FLUSH_SUBNORMALS_TO_ZERO


def test_can_generate_subnormals():
    find_any(floats().filter(lambda x: x > 0), lambda x: x < float_info.min)
    find_any(floats().filter(lambda x: x > 0), lambda x: x < float_info.min)


@pytest.mark.parametrize(
    "min_value, max_value", [(None, None), (-1, 0), (0, 1), (-1, 1)]
)
@pytest.mark.parametrize(
    "width, smallest_normal",
    [(16, 2 ** -14), (32, 2 ** -126), (64, 2 ** -1022)],
    ids=["16", "32", "64"],
)
def test_does_not_generate_subnormals_when_disallowed(
    width,
    smallest_normal,
    min_value,
    max_value,
):
    strat = floats(
        min_value=min_value,
        max_value=max_value,
        allow_subnormal=False,
        width=width,
    )
    strat = strat.filter(lambda x: x != 0.0 and not math.isnan(x) and not math.isinf(x))
    assert_all_examples(strat, lambda x: x <= -smallest_normal or x >= smallest_normal)


def kw(**kwargs):
    id_ = ", ".join(f"{k}={v!r}" for k, v in kwargs.items())
    return pytest.param(kwargs, id=id_)


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
        kw(allow_subnormal=True, min_value=-1, max_value=1),
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
    allow_subnormal = kwargs["allow_subnormal"]
    del kwargs["allow_subnormal"]
    strat = floats(**kwargs).filter(lambda x: x != 0)
    if allow_subnormal:
        find_any(strat, lambda x: -float_info.min < x < float_info.min)
    else:
        assert_no_examples(strat, lambda x: -float_info.min < x < float_info.min)
