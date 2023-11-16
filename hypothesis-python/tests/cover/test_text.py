# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

from hypothesis.strategies._internal.strings import OneCharStringStrategy


def test_rewriting_integers_covers_right_range():
    strategy = OneCharStringStrategy.from_characters_args()
    rewritten = [ord(strategy.intervals.char_in_shrink_order(i)) for i in range(256)]
    assert rewritten != list(range(256))
    assert sorted(rewritten) == sorted(range(256))
