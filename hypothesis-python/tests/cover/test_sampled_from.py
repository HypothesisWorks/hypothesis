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

import enum
import collections

from hypothesis import HealthCheck, given, settings
from hypothesis.errors import Unsatisfiable
from tests.common.utils import fails_with, checks_deprecated_behaviour
from hypothesis.strategies import sets, sampled_from

an_enum = enum.Enum('A', 'a b c')

an_ordereddict = collections.OrderedDict([('a', 1), ('b', 2), ('c', 3)])


@checks_deprecated_behaviour
def test_can_sample_sets_while_deprecated():
    assert sampled_from(set('abc')).example() in 'abc'


def test_can_sample_sequence_without_warning():
    sampled_from([1, 2, 3]).example()


def test_can_sample_ordereddict_without_warning():
    sampled_from(an_ordereddict).example()


@given(sampled_from(an_enum))
def test_can_sample_enums(member):
    assert isinstance(member, an_enum)


@given(sets(sampled_from(list(range(100))), min_size=100))
def test_entire_large_set_with_sampled_from(x):
    assert x == set(range(100))


@given(sets(sampled_from([1, 2]), min_size=2))
def test_fast_path_can_bail_without_filter_too_much(x):
    assert x == {1, 2}


@given(sets(sampled_from([1, 1, 2]), min_size=2, max_size=3))
def test_fast_path_lowers_max_size(x):
    assert x == {1, 2}


@fails_with(Unsatisfiable)
@settings(suppress_health_check=HealthCheck.all())
@given(sets(sampled_from([1, 2]), min_size=3))
def test_impossible_fast_path_fails(x):
    assert False
