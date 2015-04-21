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
from hypothesis.utils.show import show
from hypothesis.internal.debug import minimal_elements


@pytest.mark.parametrize(
    'spec', standard_types, ids=list(map(show, standard_types)))
def test_all_minimal_elements_reify(spec):
    random = Random(hashlib.md5((
        show(spec) + ':test_all_minimal_elements_round_trip_via_the_database'
    ).encode('utf-8')).digest())
    strat = strategy(spec, Settings(average_list_length=2))
    for elt in minimal_elements(strat, random):
        strat.reify(elt)
