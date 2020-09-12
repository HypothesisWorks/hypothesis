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

import math
from itertools import islice

import pytest

from hypothesis import assume, strategies as st
from hypothesis.errors import UnsatisfiedAssumption
from hypothesis.internal.conjecture.shrinking import dfas
from tests.quality.test_shrinking_order import iter_values


@st.composite
def non_integer_floats(draw):
    result = draw(st.floats())
    assume(math.isfinite(result) and result != int(result))
    return result


@pytest.fixture
def normalize_kwargs(request):
    if request.config.getoption("--hypothesis-learn-to-normalize"):
        return {"allowed_to_update": True, "required_successes": 1000}
    else:
        return {"allowed_to_update": False, "required_successes": 10}


@pytest.mark.parametrize("n", range(10, -1, -1))
@pytest.mark.parametrize(
    "strategy",
    [st.floats(), st.text(), st.datetimes(), non_integer_floats()],
    ids=repr,
)
def test_common_strategies_normalize_small_values(strategy, n, normalize_kwargs):

    excluded = list(map(repr, islice(iter_values(strategy, unique_by=repr), n)))

    def test_function(data):
        try:
            v = data.draw(strategy)
        except UnsatisfiedAssumption:
            data.mark_invalid()
        data.output = repr(v)
        if repr(v) not in excluded:
            data.mark_interesting()

    dfas.normalize(repr(strategy), test_function, **normalize_kwargs)


@pytest.mark.parametrize("strategy", [st.emails(), st.complex_numbers()], ids=repr)
def test_harder_strategies_normalize_to_minimal(strategy, normalize_kwargs):
    import random

    random.seed(0)

    def test_function(data):
        try:
            v = data.draw(strategy)
        except UnsatisfiedAssumption:
            data.mark_invalid()
        data.output = repr(v)
        data.mark_interesting()

    dfas.normalize(repr(strategy), test_function, **normalize_kwargs)
