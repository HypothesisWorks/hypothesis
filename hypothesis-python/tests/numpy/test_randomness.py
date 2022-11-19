# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import numpy as np

from hypothesis import given
from hypothesis.strategies import none


def test_numpy_prng_is_seeded():
    prng_state = np.random.get_state()

    @given(none())
    def inner(_):
        # Hypothesis sets seed to 0 by default
        implicitly_seeded_val = np.random.bytes(10)

        np.random.seed(0)
        explicitly_seeded_val = np.random.bytes(10)

        assert (
            implicitly_seeded_val == explicitly_seeded_val
        ), "Numpy random module should be reproducible"

    inner()

    np.testing.assert_array_equal(
        np.random.get_state()[1], prng_state[1], "State was not restored."
    )
