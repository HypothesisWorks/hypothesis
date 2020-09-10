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

SHOULD_NOT_IMPORT_NUMPY = """
import sys
from hypothesis import given, strategies as st

@given(st.integers() | st.floats() | st.sampled_from(["a", "b"]))
def test_no_numpy_import(x):
    assert "numpy" not in sys.modules
"""


def test_hypothesis_is_not_the_first_to_import_numpy(testdir):
    # We only import numpy if the user did so first.
    result = testdir.runpytest(testdir.makepyfile(SHOULD_NOT_IMPORT_NUMPY))
    result.assert_outcomes(passed=1, failed=0)
