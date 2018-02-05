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

import pytest

from hypothesis import seed, given, settings
from hypothesis import strategies as st
from tests.common.utils import validate_deprecation
from hypothesis.database import InMemoryExampleDatabase


@pytest.mark.parametrize('dec', [
    settings(database=InMemoryExampleDatabase(), derandomize=True), seed(1)
])
def test_deprecated_determinism_with_database(dec):
    @dec
    @given(st.booleans())
    def test(i):
        raise ValueError()

    with pytest.raises(ValueError):
        test()

    with validate_deprecation():
        with pytest.raises(ValueError):
            test()
