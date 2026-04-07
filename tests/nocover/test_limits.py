# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

from hypothesis import given, settings, strategies as st

from tests.common.utils import Why, xfail_on_crosshair


@xfail_on_crosshair(Why.other, strict=False)  # might run fewer
def test_max_examples_are_respected():
    counter = 0

    @given(st.random_module(), st.integers())
    @settings(max_examples=100)
    def test(rnd, i):
        nonlocal counter
        counter += 1

    test()
    assert counter == 100
