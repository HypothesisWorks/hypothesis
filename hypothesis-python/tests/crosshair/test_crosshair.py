# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

from contextlib import nullcontext

import crosshair
import pytest

from hypothesis import Phase, Verbosity, given, settings, strategies as st
from hypothesis.database import InMemoryExampleDatabase

from tests.common.utils import capture_observations


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


@pytest.mark.parametrize(
    "strategy, use_observability, expected_choices",
    [
        (st.integers(), False, 1),
        # we add an additional path constraint to ints in to_jsonable.
        (st.integers(), True, 2),
        (st.text(), False, 1),
        (st.text(), True, 1),
        (st.booleans(), False, 2),
        (st.booleans(), True, 2),
        (st.floats(), False, 6),
        (st.floats(), True, 6),
        (st.binary(), False, 1),
        (st.binary(), True, 1),
    ],
)
def test_no_path_constraints_are_added_to_symbolic_values(
    strategy, use_observability, expected_choices
):
    # check that we don't interact with the returned crosshair symbolics in a
    # way that would add path constraints.
    #
    # For most of the five choice sequence types, crosshair represents them as a
    # single decision. Floats uses a more complicated z3 representation. But
    # I have no idea why booleans use 2 choices instead of 1.

    # limit to one example to prevent crosshair from raising e.g.
    # BackendCannotProceed(scope="verified") and switching to the hypothesis
    # provider
    @given(strategy)
    @settings(
        backend="crosshair", database=None, phases={Phase.generate}, max_examples=1
    )
    def f(value):
        assert (
            len(crosshair.statespace.context_statespace().choices_made)
            == expected_choices
        )

    with capture_observations() if use_observability else nullcontext():
        f()
