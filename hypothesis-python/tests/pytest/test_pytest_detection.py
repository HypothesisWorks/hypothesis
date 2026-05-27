# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import subprocess
import sys

from hypothesis import core


def test_is_running_under_pytest():
    assert core.running_under_pytest


FILE_TO_RUN = """
import hypothesis.core as core
assert not core.running_under_pytest
"""


def test_is_not_running_under_pytest(tmp_path):
    pyfile = tmp_path / "test.py"
    pyfile.write_text(FILE_TO_RUN, encoding="utf-8")
    subprocess.check_call([sys.executable, str(pyfile)])


DOES_NOT_IMPORT_HYPOTHESIS = """
import sys

def test_pytest_plugin_does_not_import_hypothesis():
    assert "hypothesis" not in sys.modules
"""


def test_plugin_does_not_import_pytest(testdir):
    testdir.makepyfile(DOES_NOT_IMPORT_HYPOTHESIS)
    testdir.runpytest_subprocess().assert_outcomes(passed=1)
