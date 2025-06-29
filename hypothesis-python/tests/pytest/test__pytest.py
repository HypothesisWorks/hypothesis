# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import os
import subprocess
import sys

TESTSUITE = """
from hypothesis import given
from hypothesis import strategies as st
import _pytest

@given(st.integers())
def test_a(n):
    pass

test_a()
"""


def test_import_just_private_pytest_works(testdir):
    # importing just _pytest does not import its submodules like _pytest.outcomes.
    # Ensure we don't rely on this by writing conditional imports like
    # `if "_pytest" in sys.modules: sys.modules["_pytest"].outcomes`.
    script = testdir.makepyfile(TESTSUITE)
    result = subprocess.run(
        [sys.executable, script],
        # some hypothesis plugins (trio) import pytest, making this test pass
        # even when hypothesis has a bug. This was the case for my local installation,
        # and I am including this here on the off chance our CI setup has a similar
        # install situation. I don't want to wait for another regression to find out
        # this test doesn't work.
        env=os.environ | {"HYPOTHESIS_NO_PLUGINS": "1"},
    )
    assert result.returncode == 0
