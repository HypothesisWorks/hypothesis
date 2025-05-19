# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import crosshair
import pytest
from hypothesis_crosshair_provider.crosshair_provider import CrossHairPrimitiveProvider

from hypothesis import Phase, Verbosity, given, settings, strategies as st
from hypothesis.database import InMemoryExampleDatabase
from hypothesis.internal.conjecture.providers import COLLECTION_DEFAULT_MAX_SIZE
from hypothesis.internal.intervalsets import IntervalSet
from hypothesis.vendor.pretty import pretty

from tests.common.utils import capture_observations
from tests.conjecture.common import float_constr, integer_constr, string_constr


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


def count_choices_for(choice_type, constraints):
    # returns the number of choices that crosshair makes for this draw, before
    # hypothesis ever has a chance to interact with it.
    provider = CrossHairPrimitiveProvider()
    with provider.per_test_case_context_manager():
        assert len(crosshair.statespace.context_statespace().choices_made) == 0
        getattr(provider, f"draw_{choice_type}")(**constraints)
        return len(crosshair.statespace.context_statespace().choices_made)


@pytest.mark.parametrize(
    "strategy, expected_choices",
    [
        (st.integers(), lambda: count_choices_for("integer", integer_constr())),
        (st.floats(), lambda: count_choices_for("float", float_constr())),
        (
            st.binary(),
            lambda: count_choices_for(
                "bytes", {"min_size": 0, "max_size": COLLECTION_DEFAULT_MAX_SIZE}
            ),
        ),
        (st.booleans(), lambda: count_choices_for("boolean", {})),
        (
            st.text(),
            lambda: count_choices_for(
                "string", string_constr(IntervalSet.from_string("a"))
            ),
        ),
    ],
    ids=pretty,
)
def test_no_path_constraints_are_added_to_symbolic_values(strategy, expected_choices):
    # check that we don't interact with returned symbolics from the crosshair
    # provider in a way that would add decisions to crosshair's state space (ie
    # add path constraints).

    expected_choices = expected_choices()
    # skip the first call, which is ChoiceTemplate(type="simplest") with the
    # hypothesis backend.
    called = False

    # limit to one example to prevent crosshair from raising e.g.
    # BackendCannotProceed(scope="verified") and switching to the hypothesis
    # provider
    @given(strategy)
    @settings(
        backend="crosshair", database=None, phases={Phase.generate}, max_examples=2
    )
    def f(value):
        nonlocal called
        if not called:
            called = True
            return
        # if this test ever fails, we will replay it without crosshair, in which
        # case the statespace is None.
        statespace = crosshair.statespace.optional_context_statespace()
        assert statespace is not None, "this test failed under crosshair"
        assert len(statespace.choices_made) == expected_choices

    f()


@pytest.mark.parametrize(
    "strategy, extra_observability",
    [
        # we add an additional path constraint to ints in to_jsonable.
        (st.integers(), 1),
        (st.text(), 0),
        (st.booleans(), 0),
        (st.floats(), 0),
        (st.binary(), 0),
    ],
)
def test_observability_and_verbosity_dont_add_choices(strategy, extra_observability):
    choices = {}
    # skip the first call, which is ChoiceTemplate(type="simplest") with the
    # hypothesis backend.
    called = False

    @given(strategy)
    @settings(backend="crosshair", database=None, max_examples=2)
    def f_normal(value):
        nonlocal called
        if called:
            choices["normal"] = len(
                crosshair.statespace.context_statespace().choices_made
            )
        called = True

    f_normal()
    called = False

    @given(strategy)
    @settings(
        backend="crosshair", database=None, max_examples=2, verbosity=Verbosity.debug
    )
    def f_verbosity(value):
        nonlocal called
        if called:
            choices["verbosity"] = len(
                crosshair.statespace.context_statespace().choices_made
            )
        called = True

    f_verbosity()
    called = False

    @given(strategy)
    @settings(backend="crosshair", database=None, max_examples=2)
    def f_observability(value):
        nonlocal called
        if called:
            choices["observability"] = len(
                crosshair.statespace.context_statespace().choices_made
            )
        called = True

    with capture_observations():
        f_observability()

    assert (
        choices["normal"]
        == (choices["observability"] - extra_observability)
        == choices["verbosity"]
    )
