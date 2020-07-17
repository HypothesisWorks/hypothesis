# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Most of this work is copyright (C) 2013-2020 David R. MacIver
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

from pytest import raises

from hypothesis import Verbosity, given, settings, strategies as st
from tests.common.utils import no_shrink


def test_nesting_1():
    @given(st.integers(0, 100))
    @settings(max_examples=5, database=None, deadline=None)
    def test_blah(x):
        @given(st.integers())
        @settings(
            max_examples=100, phases=no_shrink, database=None, verbosity=Verbosity.quiet
        )
        def test_nest(y):
            if y >= x:
                raise ValueError()

        with raises(ValueError):
            test_nest()

    test_blah()
