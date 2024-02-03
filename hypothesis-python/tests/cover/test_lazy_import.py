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

from tests.common.utils import skipif_emscripten

SHOULD_NOT_IMPORT_TEST_RUNNERS = """
import sys
import unittest
from hypothesis import given, strategies as st

class TestDoesNotImportRunners(unittest.TestCase):
    strat = st.integers() | st.floats() | st.sampled_from(["a", "b"])

    @given(strat)
    def test_does_not_import_unittest2(self, x):
        assert "unittest2" not in sys.modules

    @given(strat)
    def test_does_not_import_nose(self, x):
        assert "nose" not in sys.modules

    @given(strat)
    def test_does_not_import_pytest(self, x):
        assert "pytest" not in sys.modules

if __name__ == '__main__':
    unittest.main()
"""


@skipif_emscripten
def test_hypothesis_does_not_import_test_runners(tmp_path):
    # We obviously can't use pytest to check that pytest is not imported,
    # so for consistency we use unittest for all three non-stdlib test runners.
    # It's unclear which of our dependencies is importing unittest, but
    # since I doubt it's causing any spurious failures I don't really care.
    # See https://github.com/HypothesisWorks/hypothesis/pull/2204
    fname = tmp_path / "test.py"
    fname.write_text(SHOULD_NOT_IMPORT_TEST_RUNNERS, encoding="utf-8")
    subprocess.check_call(
        [sys.executable, str(fname)],
        env={**os.environ, "HYPOTHESIS_NO_PLUGINS": "1"},
    )
