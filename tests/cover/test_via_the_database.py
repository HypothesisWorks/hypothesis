# coding=utf-8

# Copyright (C) 2013-2015 David R. MacIver (david@drmaciver.com)

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

from __future__ import division, print_function, absolute_import, \
    unicode_literals

import hashlib
from random import Random

import pytest
from hypothesis import Settings, strategy
from tests.common import standard_types
from hypothesis.strategies import lists, booleans
from hypothesis.utils.show import show
from hypothesis.internal.debug import via_database, some_template, \
    minimal_elements
from hypothesis.internal.compat import hrange
from hypothesis.searchstrategy.strategies import BadData


@pytest.mark.parametrize(
    'spec', standard_types, ids=list(map(show, standard_types)))
def test_round_tripping_via_the_database(spec):
    random = Random(hashlib.md5(
        (show(spec) + ':test_round_tripping_via_the_database').encode('utf-8')
    ).digest())
    strat = strategy(spec)
    template = some_template(strat, random)
    strat.from_basic(strat.to_basic(template))
    template_via_db = via_database(spec, strat, template)
    assert show(strat.reify(template)) == show(strat.reify(template_via_db))


@pytest.mark.parametrize(
    'spec', standard_types, ids=list(map(show, standard_types)))
def test_round_tripping_lists_via_the_database(spec):
    random = Random(hashlib.md5(
        (show(spec) + ':test_round_tripping_via_the_database').encode('utf-8')
    ).digest())
    strat = lists(spec)
    template = some_template(strat, random)
    template_via_db = via_database(spec, strat, template)
    assert show(strat.reify(template)) == show(strat.reify(template_via_db))


@pytest.mark.parametrize(
    'spec', standard_types, ids=list(map(show, standard_types)))
def test_all_minimal_elements_round_trip_via_the_database(spec):
    random = Random(hashlib.md5((
        show(spec) + ':test_all_minimal_elements_round_trip_via_the_database'
    ).encode('utf-8')).digest())
    strat = strategy(spec, Settings(average_list_length=2))
    for elt in minimal_elements(strat, random):
        elt_via_db = via_database(spec, strat, elt)
        assert show(strat.reify(elt)) == show(strat.reify(elt_via_db))
        elt_via_db_2 = via_database(spec, strat, elt_via_db)
        assert elt_via_db == elt_via_db_2


__minimal_basic = None


def minimal_basic():
    global __minimal_basic
    if __minimal_basic is None:
        random = Random('__minimal_templates_as_basic_data')
        __minimal_basic = []
        for typ in standard_types:
            strat = strategy(typ, Settings(average_list_length=2))
            for m in minimal_elements(strat, random):
                __minimal_basic.append(strat.to_basic(m))
        for i in hrange(10):
            __minimal_basic.append(list(hrange(i)))
            __minimal_basic.append([None] * i)
        __minimal_basic.append(None)
    return __minimal_basic


@pytest.mark.parametrize(
    'strat', standard_types, ids=list(map(show, standard_types)))
def test_only_raises_bad_data_on_minimal(strat):
    for m in minimal_basic():
        try:
            strat.from_basic(m)
        except BadData:
            pass


def test_lists_of_incompatible_sizes_are_checked():
    s10 = lists(booleans(), min_size=10)
    s2 = lists(booleans(), max_size=9)

    x10 = s10.to_basic(some_template(s10))
    x2 = s2.to_basic(some_template(s2))
    with pytest.raises(BadData):
        s2.from_basic(x10)
    with pytest.raises(BadData):
        s10.from_basic(x2)
