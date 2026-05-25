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

from hypothesis import Phase, settings
from hypothesis.errors import Unsatisfiable
from hypothesis.strategies import lists

from tests.common import standard_types
from tests.common.debug import minimal


@pytest.mark.parametrize("spec", standard_types, ids=repr)
def test_can_collectively_minimize(spec):
    n = 10
    try:
        xs = minimal(
            lists(spec, min_size=n, max_size=n),
            lambda x: len(set(map(repr, x))) >= 2,
            settings(max_examples=2000, phases=(Phase.generate, Phase.shrink)),
        )
        assert len(xs) == n
        assert 2 <= len(set(map(repr, xs))) <= 3
    except Unsatisfiable:
        pass
