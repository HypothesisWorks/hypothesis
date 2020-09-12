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

from hypothesis import given, strategies as st
from hypothesis.strategies._internal.types import _global_type_lookup

TYPES = sorted((x for x in _global_type_lookup if x.__module__ != "typing"), key=str)


def everything_except(excluded_types):
    """Recipe copied from the docstring of ``from_type``"""
    return (
        st.from_type(type)
        .flatmap(st.from_type)
        .filter(lambda x: not isinstance(x, excluded_types))
    )


@given(
    excluded_types=st.lists(
        st.sampled_from(TYPES), min_size=1, max_size=3, unique=True
    ).map(tuple),
    data=st.data(),
)
def test_recipe_for_everything_except(excluded_types, data):
    value = data.draw(everything_except(excluded_types))
    assert not isinstance(value, excluded_types)
