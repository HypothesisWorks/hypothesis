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


from hypothesis import find, settings, strategies as st
import pytest
from hypothesis.internal.conjecture.engine import ConjectureRunner
from random import Random


@st.deferred
def tree():
    return st.none() | st.tuples(tree, tree)


BASE_STRATEGIES = [
    tree,
    st.text(),
    st.fractions(),
    st.datetimes(),
    st.floats(allow_nan=False),
    st.integers(),
    st.binary(),
    st.lists(st.integers(), unique=True),
]

STRATEGIES_TO_NORMALIZE = BASE_STRATEGIES + [
    st.tuples(u, v)
    for u in BASE_STRATEGIES
    for v in BASE_STRATEGIES
]


@pytest.mark.parametrize('strategy', STRATEGIES_TO_NORMALIZE, ids=list(map(repr, STRATEGIES_TO_NORMALIZE)))
def test_should_normalize_small_examples(strategy):
    seen = set()

    results = {}

    def test_function(data):
        s = data.draw(strategy)
        if repr(s) not in seen:
            results[bytes(data.buffer)] = repr(s)
            data.mark_interesting()

    def result():
        runner = ConjectureRunner(test_function, settings=settings(database=None, max_examples=10 ** 6, report_multiple_bugs=False))
        runner.run()
        v, = runner.interesting_examples.values()
        return v.buffer

    for _ in range(10):
        buf = result()
        for _ in range(3):
            newbuf = result()
            assert newbuf == buf
        seen.add(results[buf])
