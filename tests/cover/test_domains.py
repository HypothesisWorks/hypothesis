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

import math
import decimal

import pytest

import hypothesis.strategies as st
from hypothesis import find, given
from tests.common.utils import fails
from hypothesis.searchstrategy import domains


@given(st.domains())
def test_all_domains_are_valid(domain):
    labels = domain.split(".")
    top_level = labels.pop()

    assert len(domain) <= domains.MAX_DOMAIN_SIZE
    assert len(labels) <= domains.MAX_LABEL_COUNT
    assert max(map(len, labels)) <= domains.MAX_LABEL_SIZE
    assert top_level in domains.SUFFIX_LIST

def test_minimizes_to_second_level_domain():
    domain = find(st.domains(), lambda d: d.count(".") == 1)
    assert domain.count(".") == 1
