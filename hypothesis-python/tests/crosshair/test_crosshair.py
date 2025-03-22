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

from hypothesis import Verbosity, given, settings, strategies as st
from hypothesis.database import InMemoryExampleDatabase


@pytest.mark.parametrize("verbosity", list(Verbosity))
def test_crosshair_works_for_all_verbosities(verbosity):
    # check that we aren't realizing symbolics early in debug prints and killing
    # test effectiveness.
    @given(st.integers())
    @settings(backend="crosshair", verbosity=verbosity, database=None)
    def f(n):
        assert n != 123456

    with pytest.raises(AssertionError):
        f()


@pytest.mark.parametrize("verbosity", list(Verbosity))
def test_crosshair_works_for_all_verbosities_data(verbosity):
    # data draws have their own print path
    @given(st.data())
    @settings(backend="crosshair", verbosity=verbosity, database=None)
    def f(data):
        n = data.draw(st.integers())
        assert n != 123456

    with pytest.raises(AssertionError):
        f()


def test_hypothesis_realizes_on_fatal_error():
    # BaseException or internal hypothesis failures have a different database save
    # path. Make sure we realize symbolic values on that path. This test is a bit
    # of a no-op because we're really relying on our realization validation to
    # pass here.
    db = InMemoryExampleDatabase()

    @given(st.integers())
    @settings(database=db, backend="crosshair")
    def f(n):
        raise BaseException("marker")

    with pytest.raises(BaseException, match="marker"):
        f()
