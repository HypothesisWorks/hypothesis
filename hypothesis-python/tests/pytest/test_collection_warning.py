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

pytest_plugins = "pytester"

INI = """
[pytest]
norecursedirs = .svn tmp whatever*
"""

TEST_SCRIPT = """
def test_noop():
    pass
"""


@pytest.mark.skipif(int(pytest.__version__.split(".")[0]) < 7, reason="hook is new")
def test_collection_warning(pytester):
    pytester.mkdir(".hypothesis")
    pytester.path.joinpath("pytest.ini").write_text(INI, encoding="utf-8")
    pytester.path.joinpath("test_ok.py").write_text(TEST_SCRIPT, encoding="utf-8")
    pytester.path.joinpath(".hypothesis/test_bad.py").write_text(
        TEST_SCRIPT.replace("pass", "raise Exception"), encoding="utf-8"
    )

    result = pytester.runpytest_subprocess()
    result.assert_outcomes(passed=1, warnings=1)
    assert "Skipping collection of '.hypothesis'" in "\n".join(result.outlines)
