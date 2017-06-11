# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2017 David R. MacIver
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

from hypothesis import given, settings
from hypothesis.errors import HypothesisDeprecationWarning
from tests.common.utils import fails_with
from hypothesis.strategies import sampled_from

an_enum = enum.Enum('A', 'a b c')

an_ordereddict = collections.OrderedDict([('a', 1), ('b', 2), ('c', 3)])


@given(sampled_from((1, 2)))
@settings(min_satisfying_examples=10)
def test_can_handle_sampling_from_fewer_than_min_satisfying(v):
    pass


@fails_with(HypothesisDeprecationWarning)
def test_cannot_sample_sets_in_strict_mode():
    with settings(strict=True):
        sampled_from(set('abc')).example()


def test_can_sample_sets_while_deprecated():
    with settings(strict=False):
        assert sampled_from(set('abc')).example() in 'abc'


def test_can_sample_sequence_without_warning():
    with settings(strict=True):
        sampled_from([1, 2, 3]).example()


def test_can_sample_ordereddict_without_warning():
    with settings(strict=True):
        sampled_from(an_ordereddict).example()


@given(sampled_from(an_enum))
def test_can_sample_enums(member):
    with settings(strict=True):
        assert isinstance(member, an_enum)
