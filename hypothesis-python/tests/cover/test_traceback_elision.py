# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import traceback

import pytest

from hypothesis import Verbosity, given, settings, strategies as st


@pytest.mark.parametrize("verbosity", [Verbosity.normal, Verbosity.debug])
@pytest.mark.parametrize("env_value", ["", "1"])
def test_tracebacks_omit_hypothesis_internals(monkeypatch, env_value, verbosity):
    monkeypatch.setenv("HYPOTHESIS_NO_TRACEBACK_TRIM", env_value)

    @settings(verbosity=verbosity)
    @given(st.just(False))
    def simplest_failure(x):
        raise ValueError

    try:
        simplest_failure()
    except ValueError as e:
        tb = traceback.extract_tb(e.__traceback__)
        # Unless in debug mode, Hypothesis adds 2 frames:
        # _reraise_trimmed_error and wrapped_test.
        # (5 frames: this one, simplest_failure, _reraise_trimmed_error,
        # wrapped_test, raise ValueError)
        if verbosity < Verbosity.debug and not env_value:
            assert len(tb) == 5
        else:
            assert len(tb) >= 6
