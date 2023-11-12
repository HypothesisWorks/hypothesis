# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

from hypothesis.internal.conjecture.junkdrawer import char_rewrite_integer, Z_point, zero_point
from hypothesis.strategies._internal.strings import OneCharStringStrategy


def test_rewriting_integers_covers_right_range():
    strategy = OneCharStringStrategy.from_characters_args()

    zero_point_ = zero_point(strategy.intervals)
    Z_point_ = Z_point(strategy.intervals)
    rewritten = [
        char_rewrite_integer(
            i,
            zero_point=zero_point_,
            Z_point=Z_point_
        ) for i in range(256)
    ]
    assert sorted(rewritten) == sorted(range(256))
