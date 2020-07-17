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

from hypothesis import given, strategies as st
from hypothesis.strategies import integers, lists


@pytest.mark.parametrize(
    ("specifier", "condition"),
    [(integers(), lambda x: x > 1), (lists(integers()), bool)],
)
def test_filter_correctly(specifier, condition):
    @given(specifier.filter(condition))
    def test_is_filtered(x):
        assert condition(x)

    test_is_filtered()


# A variety of strategies that generate the integers 1-20 inclusive, but might
# differ in their support for special-case filtering.
one_to_twenty_strategies = [
    st.integers(1, 20),
    st.integers(0, 19).map(lambda x: x + 1),
    st.sampled_from(range(1, 21)),
    st.sampled_from(range(0, 20)).map(lambda x: x + 1),
]


@pytest.mark.parametrize("base", one_to_twenty_strategies)
@given(
    data=st.data(),
    forbidden_values=st.lists(st.integers(1, 20), max_size=19, unique=True),
)
def test_chained_filters_agree(data, forbidden_values, base):
    def forbid(s, forbidden):
        """Helper function to avoid Python variable scoping issues."""
        return s.filter(lambda x: x != forbidden)

    s = base
    for forbidden in forbidden_values:
        s = forbid(s, forbidden)

    x = data.draw(s)
    assert 1 <= x <= 20
    assert x not in forbidden_values


@pytest.mark.parametrize("base", one_to_twenty_strategies)
def test_chained_filters_repr(base):
    def foo(x):
        return x != 0

    def bar(x):
        return x != 2

    filtered = base.filter(foo)
    chained = filtered.filter(bar)
    assert repr(chained) == "%r.filter(foo).filter(bar)" % (base,)
    assert repr(filtered) == "%r.filter(foo)" % (base,)
