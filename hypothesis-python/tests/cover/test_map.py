# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

from hypothesis import assume, given, strategies as st
from hypothesis.strategies._internal.lazy import unwrap_strategies

from tests.common.debug import assert_no_examples


@given(st.integers().map(lambda x: assume(x % 3 != 0) and x))
def test_can_assume_in_map(x):
    assert x % 3 != 0


def test_assume_in_just_raises_immediately():
    assert_no_examples(st.just(1).map(lambda x: assume(x == 2)))


def test_identity_map_is_noop():
    s = unwrap_strategies(st.integers())
    assert s.map(lambda x: x) is s
