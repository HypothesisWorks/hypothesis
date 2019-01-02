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
# obtain one at http://mozilla.org/MPL/2.0/.
#
# END HEADER

from __future__ import absolute_import, division, print_function

import pytest

from hypothesis import given, seed, settings, strategies as st
from hypothesis.database import InMemoryExampleDatabase
from tests.common.utils import validate_deprecation


@pytest.mark.parametrize(
    "dec", [settings(database=InMemoryExampleDatabase(), derandomize=True), seed(1)]
)
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
