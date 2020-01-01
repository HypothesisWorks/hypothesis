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

from hypothesis import assume, given, strategies as st
from tests.common.debug import assert_no_examples


@given(st.integers().map(lambda x: assume(x % 3 != 0) and x))
def test_can_assume_in_map(x):
    assert x % 3 != 0


def test_assume_in_just_raises_immediately():
    assert_no_examples(st.just(1).map(lambda x: assume(x == 2)))
