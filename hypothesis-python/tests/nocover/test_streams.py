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

from itertools import islice

from hypothesis import HealthCheck, given, settings
from hypothesis.internal.compat import integer_types
from hypothesis.strategies import integers, streaming
from tests.common.utils import checks_deprecated_behaviour


@checks_deprecated_behaviour
def test_streams_are_arbitrarily_long():
    @settings(suppress_health_check=[HealthCheck.too_slow])
    @given(streaming(integers()))
    def test(ss):
        for i in islice(ss, 100):
            assert isinstance(i, integer_types)

    test()
