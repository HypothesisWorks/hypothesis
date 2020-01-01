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

import numpy as np

from hypothesis import given
from hypothesis.strategies import none


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
