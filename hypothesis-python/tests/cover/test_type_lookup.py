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
from hypothesis import given
from hypothesis._strategies import _strategies
from hypothesis.errors import HypothesisDeprecationWarning, InvalidArgument
from hypothesis.internal.compat import PY2, integer_types
from hypothesis.searchstrategy import types
from hypothesis.searchstrategy.types import _global_type_lookup

# Build a set of all types output by core strategies
blacklist = [
    "builds",
    "iterables",
    "permutations",
    "random_module",
    "randoms",
    "runner",
    "sampled_from",
]
types_with_core_strat = set(integer_types)
for thing in (
    getattr(st, name)
    for name in sorted(_strategies)
    if name in dir(st) and name not in blacklist
):
    for n in range(3):
        try:
            ex = thing(*([st.nothing()] * n)).example()
            types_with_core_strat.add(type(ex))
            break
        except (TypeError, InvalidArgument, HypothesisDeprecationWarning):
            continue


@pytest.mark.parametrize("typ", sorted(types_with_core_strat, key=str))
def test_resolve_core_strategies(typ):
    @given(st.from_type(typ))
    def inner(ex):
        if PY2 and issubclass(typ, integer_types):
            assert isinstance(ex, integer_types)
        else:
            assert isinstance(ex, typ)

    inner()


def test_lookup_knows_about_all_core_strategies():
    cannot_lookup = types_with_core_strat - set(types._global_type_lookup)
    assert not cannot_lookup


@pytest.mark.parametrize("typ", sorted(_global_type_lookup, key=str))
@given(data=st.data())
def test_can_generate_from_all_registered_types(data, typ):
    value = data.draw(st.from_type(typ), label="value")
    assert isinstance(value, typ)
