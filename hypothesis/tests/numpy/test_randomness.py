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
from hypothesis.strategies import none, randoms


def test_numpy_prng_is_seeded():
    first = []
    prng_state = np.random.get_state()

    @given(none())
    def inner(_):
        val = np.random.bytes(10)
        if not first:
            first.append(val)
        assert val == first[0], "Numpy random module should be reproducible"

    inner()

    np.testing.assert_array_equal(
        np.random.get_state()[1], prng_state[1], "State was not restored."
    )


@given(randoms(use_true_random=False))
def test_randoms_can_choose_from_array(rnd):
    # make sure our random impl doesn't check bool(arr), which is an error for numpy
    arrays
    assert rnd.choice(np.array([1, 2, 3])) in (1, 2, 3)
