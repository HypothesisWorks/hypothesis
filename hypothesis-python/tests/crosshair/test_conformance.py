# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

from crosshair.core import IgnoreAttempt, NotDeterministic, UnexploredPath
from hypothesis_crosshair_provider.crosshair_provider import CrossHairPrimitiveProvider

from hypothesis import settings, strategies as st
from hypothesis.internal.conjecture.provider_conformance import run_conformance_test


def test_provider_conformance_crosshair():
    # Hypothesis can in theory pass values of any type to `realize`,
    # but the default strategy in the conformance test here acts too much like a
    # fuzzer for crosshair internals here and finds very strange errors.
    _realize_objects = (
        st.integers() | st.floats() | st.booleans() | st.binary() | st.text()
    )
    run_conformance_test(
        CrossHairPrimitiveProvider,
        context_manager_exceptions=(IgnoreAttempt, UnexploredPath, NotDeterministic),
        settings=settings(max_examples=5, stateful_step_count=10),
        _realize_objects=_realize_objects,
    )
