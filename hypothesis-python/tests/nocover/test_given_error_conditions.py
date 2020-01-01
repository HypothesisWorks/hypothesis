# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Most of this work is copyright (C) 2013-2020 David R. MacIver
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

import pytest

from hypothesis import HealthCheck, given, reject, settings
from hypothesis.errors import Unsatisfiable
from hypothesis.strategies import integers


def test_raises_unsatisfiable_if_all_false():
    @given(integers())
    @settings(max_examples=50, suppress_health_check=HealthCheck.all())
    def test_assume_false(x):
        reject()

    with pytest.raises(Unsatisfiable):
        test_assume_false()
