# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2015 David R. MacIver
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

import hypothesis.strategies as st
from hypothesis import given, assume
from hypothesis.internal.conjecture.grammar import alt, cat, nil, star, \
    epsilon, literal, GrammarTable


def equiv(a, b):
    gt = GrammarTable()
    return gt.normalize(a) == gt.normalize(b)


def test_reorder_cats():
    a = literal('a')
    b = star(literal('b'))
    c = literal('c')

    assert equiv(
        cat(cat(a, b), c),
        cat(a, cat(b, c))
    )


Grammars = st.recursive(
    st.one_of(
        st.sets(st.integers()).map(lambda x: epsilon(*x)),
        st.builds(literal, st.binary()),
        st.just(nil()),
    ),
    lambda g: st.one_of(
        st.builds(star, g),
        st.lists(g).map(lambda x: cat(*x)),
        st.lists(g).map(lambda x: alt(*x)),
    )
)


@given(Grammars)
def test_can_calculate_grammar_properties(g):
    t = GrammarTable()
    n = t.normalize(nil())
    assume(t.normalize(g) != n)
    if not t.can_match_empty(g):
        assert t.valid_starts(g)


@given(Grammars)
def test_normalizing_is_identity_idempotent(g):
    t = GrammarTable()
    x = t.normalize(g)
    assert t.normalize(g) is x
    re = t.normalize(x)
    assert re == x
    assert hash(re) == hash(x)
    assert re is x


@given(Grammars)
def test_can_differentiate_by_any_match(g):
    t = GrammarTable()
    n = t.normalize(nil())
    assume(t.normalize(g) != n)
    starts = t.valid_starts(g)
    assume(starts)
    for c in starts:
        d = t.derivative(g, c)
        assert d is t.normalize(d)
        assert d != n


@given(Grammars, st.data())
def test_tags_can_be_followed_through_to_the_end(g, data):
    t = GrammarTable()
    g = t.normalize(g)
    tags = sorted(t.reachable_tags(g), key=lambda s: (type(s).__name__, s))
    target = data.draw(st.sampled_from(tags))
    while not t.can_match_empty(g):
        branches = [
            (c, t.derivative(c)) for c in t.valid_starts(g)
        ]
        choices = [
            c for c, g in branches
            if target in t.reachable_tags(g)
        ]
        assert choices
        choice = data.draw(st.sampled_from(choices))
        g = t.derivative(g, choice)
