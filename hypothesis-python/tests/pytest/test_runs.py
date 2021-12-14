# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

from hypothesis import given
from hypothesis.strategies import integers

from tests.common.utils import fails


@given(integers())
def test_ints_are_ints(x):
    pass


@fails
@given(integers())
def test_ints_are_floats(x):
    assert isinstance(x, float)
