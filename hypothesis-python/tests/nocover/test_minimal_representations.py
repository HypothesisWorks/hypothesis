# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import hypothesis.strategies as st
from hypothesis.internal.conjecture.data import ConjectureData
from hypothesis.internal.conjecture.engine import BUFFER_SIZE
from hypothesis.strategies import SearchStrategy


def minimal_buffer_for(strategy: SearchStrategy) -> bytes:
    data = ConjectureData.for_buffer(bytes(BUFFER_SIZE))
    # TODO: Not all strategies will actually produce a valid result
    # for all zero bytes. When we have one we want to test this
    # will require updating to use the shrinker.
    data.draw(strategy)
    return bytes(data.buffer)


def test_integers_have_a_one_byte_representation():
    assert len(minimal_buffer_for(st.integers())) == 1
