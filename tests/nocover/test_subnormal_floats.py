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

from hypothesis.internal.floats import width_smallest_normals
from hypothesis.strategies import floats

from tests.common.debug import assert_all_examples, find_any
from tests.common.utils import PYTHON_FTZ


def test_python_compiled_with_sane_math_options():
    """Python does not flush-to-zero, which violates IEEE-754

    The other tests that rely on subnormals are skipped when Python is FTZ
    (otherwise pytest will be very noisy), so this meta test ensures CI jobs
    still fail as we currently don't care to support such builds of Python.
    """
    assert not PYTHON_FTZ


skipif_ftz = pytest.mark.skipif(PYTHON_FTZ, reason="broken by unsafe compiler flags")


@skipif_ftz
def test_can_generate_subnormals():
    find_any(floats().filter(lambda x: x > 0), lambda x: x < float_info.min)
    find_any(floats().filter(lambda x: x < 0), lambda x: x > -float_info.min)


@skipif_ftz
@pytest.mark.parametrize(
    "min_value, max_value", [(None, None), (-1, 0), (0, 1), (-1, 1)]
)
@pytest.mark.parametrize("width", [16, 32, 64])
def test_does_not_generate_subnormals_when_disallowed(width, min_value, max_value):
    strat = floats(
        min_value=min_value,
        max_value=max_value,
        allow_subnormal=False,
        width=width,
    )
    strat = strat.filter(lambda x: x != 0.0 and math.isfinite(x))
    smallest_normal = width_smallest_normals[width]
    assert_all_examples(strat, lambda x: x <= -smallest_normal or x >= smallest_normal)
