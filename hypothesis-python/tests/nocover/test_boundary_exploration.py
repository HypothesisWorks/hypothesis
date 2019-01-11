# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Most of this work is copyright (C) 2013-2019 David R. MacIver
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

from __future__ import absolute_import, division, print_function

import pytest

import hypothesis.strategies as st
from hypothesis import HealthCheck, Verbosity, find, given, reject, settings, unlimited
from hypothesis.errors import NoSuchExample
from tests.common.utils import no_shrink


@pytest.mark.parametrize("strat", [st.text(min_size=5)])
@settings(phases=no_shrink, deadline=None, suppress_health_check=HealthCheck.all())
@given(st.data())
def test_explore_arbitrary_function(strat, data):
    cache = {}

    def predicate(x):
        try:
            return cache[x]
        except KeyError:
            return cache.setdefault(x, data.draw(st.booleans(), label=repr(x)))

    try:
        find(
            strat,
            predicate,
            settings=settings(
                max_examples=10,
                database=None,
                timeout=unlimited,
                verbosity=Verbosity.quiet,
            ),
        )
    except NoSuchExample:
        reject()
