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
from inspect import Parameter, Signature

import pytest

from hypothesis.internal.compat import ceil, floor, get_type_hints

floor_ceil_values = [
    -10.7,
    -10.3,
    -0.5,
    -0.0,
    0,
    0.5,
    10.3,
    10.7,
]


@pytest.mark.parametrize("value", floor_ceil_values)
def test_our_floor_agrees_with_math_floor(value):
    assert floor(value) == math.floor(value)


@pytest.mark.parametrize("value", floor_ceil_values)
def test_our_ceil_agrees_with_math_ceil(value):
    assert ceil(value) == math.ceil(value)


class WeirdSig:
    __signature__ = Signature(
        parameters=[Parameter(name="args", kind=Parameter.VAR_POSITIONAL)]
    )


def test_no_type_hints():
    assert get_type_hints(WeirdSig) == {}
