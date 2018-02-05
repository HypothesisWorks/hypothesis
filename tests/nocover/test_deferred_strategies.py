# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2018 David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
# CONTRIBUTING.rst for a full list of people who may hold copyright, and
# consult the git log if you need to determine who owns an individual
# contribution.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.
#
# END HEADER

from __future__ import division, print_function, absolute_import

from hypothesis import Verbosity, find, note, given, settings
from hypothesis import strategies as st
from hypothesis.errors import NoSuchExample, Unsatisfiable
from hypothesis.internal.compat import hrange


@st.composite
def mutually_recursive_strategies(draw):
    strategies = [st.none()]

    def build_strategy_for_indices(base, ixs, deferred):
        def f():
            return base(*[strategies[i] for i in ixs])
        f.__name__ = '%s([%s])' % (
            base.__name__, ', '.join(
                'strategies[%d]' % (i,) for i in ixs
            ))
        if deferred:
            return st.deferred(f)
        else:
            return f()

    n_strategies = draw(st.integers(1, 5))

    for i in hrange(n_strategies):
        base = draw(st.sampled_from((st.one_of, st.tuples)))
        indices = draw(st.lists(
            st.integers(0, n_strategies), min_size=1))
        if all(j <= i for j in indices):
            deferred = draw(st.booleans())
        else:
            deferred = True
        strategies.append(build_strategy_for_indices(base, indices, deferred))
    return strategies


@settings(deadline=None)
@given(mutually_recursive_strategies())
def test_arbitrary_recursion(strategies):
    for i, s in enumerate(strategies):
        if i > 0:
            note('strategies[%d]=%r' % (i, s))

            s.validate()

            try:
                find(s, lambda x: True, settings=settings(
                    max_shrinks=0, database=None, verbosity=Verbosity.quiet,
                    max_examples=1, max_iterations=10,
                ))
            except (Unsatisfiable, NoSuchExample):
                pass
