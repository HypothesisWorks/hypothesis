# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import pytest

from hypothesis import HealthCheck, Verbosity, given, reject, settings, strategies as st
from hypothesis.errors import Unsatisfiable

from tests.common.debug import minimal
from tests.common.utils import no_shrink


@pytest.mark.parametrize("strat", [st.text(min_size=5)])
@settings(phases=no_shrink, deadline=None, suppress_health_check=list(HealthCheck))
@given(st.data())
def test_explore_arbitrary_function(strat, data):
    cache = {}

    def predicate(x):
        try:
            return cache[x]
        except KeyError:
            return cache.setdefault(x, data.draw(st.booleans(), label=repr(x)))

    try:
        minimal(
            strat,
            predicate,
            settings=settings(
                max_examples=10, database=None, verbosity=Verbosity.quiet
            ),
        )
    except Unsatisfiable:
        reject()
