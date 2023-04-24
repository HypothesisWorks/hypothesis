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
from _hypothesis_pytestplugin import LOAD_PROFILE_OPTION

from hypothesis.version import __version__

pytest_plugins = "pytester"


CONFTEST = """
from hypothesis._settings import settings
settings.register_profile("test", settings(max_examples=1))
"""

TESTSUITE = """
from hypothesis import given
from hypothesis.strategies import integers
from hypothesis._settings import settings

def test_this_one_is_ok():
    assert settings().max_examples == 1
"""


def test_does_not_run_reporting_hook_by_default(testdir):
    script = testdir.makepyfile(TESTSUITE)
    testdir.makeconftest(CONFTEST)
    result = testdir.runpytest(script, LOAD_PROFILE_OPTION, "test")
    out = "\n".join(result.stdout.lines)
    assert "1 passed" in out
    assert "hypothesis profile" not in out
    assert __version__ in out


@pytest.mark.parametrize("option", ["-v", "--hypothesis-verbosity=verbose"])
def test_runs_reporting_hook_in_any_verbose_mode(testdir, option):
    script = testdir.makepyfile(TESTSUITE)
    testdir.makeconftest(CONFTEST)
    result = testdir.runpytest(script, LOAD_PROFILE_OPTION, "test", option)
    out = "\n".join(result.stdout.lines)
    assert "1 passed" in out
    assert "max_examples=1" in out
    assert "hypothesis profile" in out
    assert __version__ in out
