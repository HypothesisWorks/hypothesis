# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

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


# We check the wildcard import works on the module level because that's the only
# place Python actually allows us to use them.
try:
    from hypothesis.extra.numpy import *  # noqa: F403

    star_import_works = True
except AttributeError:
    star_import_works = False


def test_wildcard_import():
    assert star_import_works
