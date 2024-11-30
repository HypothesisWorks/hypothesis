# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

from hypothesis import HealthCheck, given, reject, settings
from hypothesis.errors import Unsatisfiable
from hypothesis.strategies import integers

from tests.common.utils import fails_with


@fails_with(Unsatisfiable)
@given(integers())
@settings(max_examples=50, suppress_health_check=list(HealthCheck))
def test_raises_unsatisfiable_if_all_false(x):
    reject()
