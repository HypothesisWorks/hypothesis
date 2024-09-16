# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import pytest

from hypothesis import given, strategies as st


@pytest.mark.parametrize("width", [32, 64, 128])
@pytest.mark.parametrize("keyword", ["min_magnitude", "max_magnitude"])
@given(data=st.data())
def test_magnitude_validates(width, keyword, data):
    # See https://github.com/HypothesisWorks/hypothesis/issues/3573
    component_width = width / 2
    magnitude = data.draw(
        # 1.8 is a known example that hasn't validated in the past
        st.floats(0, width=component_width) | st.just(1.8),
        label=keyword,
    )
    strat = st.complex_numbers(width=width, **{keyword: magnitude})
    data.draw(strat)
