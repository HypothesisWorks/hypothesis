# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

pytest_plugins = "pytester"

func_with_doctest = """
def hi():
    '''
    >>> i = 5
    >>> i-1
    4
    '''
"""


def test_can_run_doctests(testdir):
    script = testdir.makepyfile(func_with_doctest)
    result = testdir.runpytest(script, "--doctest-modules")
    assert result.ret == 0
