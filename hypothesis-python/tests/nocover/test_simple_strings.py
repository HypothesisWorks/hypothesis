# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import unicodedata

import pytest

from hypothesis import given, settings
from hypothesis.strategies import text


@pytest.mark.skipif(
    settings._current_profile == "crosshair",
    reason="takes ~10 minutes; many-valued realization is slow",
)
@given(text(min_size=1, max_size=1))
@settings(max_examples=2000)
def test_does_not_generate_surrogates(t):
    assert unicodedata.category(t) != "Cs"
