# coding=utf-8

# Copyright (C) 2013-2015 David R. MacIver (david@drmaciver.com)

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

from __future__ import division, print_function, absolute_import, \
    unicode_literals

import pytest
from hypothesis import given, assume, strategy
from tests.common import timeout
from hypothesis.core import _debugging_return_failing_example
from hypothesis.internal.compat import text_type, binary_type


@pytest.mark.parametrize(('string',), [(text_type,), (binary_type,)])
def test_minimal_unsorted_strings(string):
    def dedupe(xs):
        result = []
        for x in xs:
            if x not in result:
                result.append(x)
        return result

    @timeout(5)
    @given(strategy([string]).map(dedupe))
    def is_sorted(xs):
        assume(len(xs) >= 10)
        assert sorted(xs) == xs

    with _debugging_return_failing_example.with_value(True):
        result = is_sorted()[1]['xs']
        assert len(result) == 10
        assert all(len(r) <= 2 for r in result)
