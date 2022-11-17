# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

TEST_DECORATORS_ALONE = """
import hypothesis
from hypothesis.strategies import composite, none

@composite
def test_composite_is_not_a_test(draw):
    # This strategy will be instantiated, but no draws == no calls.
    return draw(none())

@hypothesis.seed(0)
def test_seed_without_given_fails():
    pass

@hypothesis.example(x=None)
def test_example_without_given_fails():
    pass

@hypothesis.reproduce_failure(hypothesis.__version__, b"AA==")
def test_repro_without_given_fails():
    pass
"""


def test_decorators_without_given_should_fail(testdir):
    script = testdir.makepyfile(TEST_DECORATORS_ALONE)
    result = testdir.runpytest(script)
    result.assert_outcomes(failed=4)
    assert "pytest_runtest_call" not in "\n".join(result.outlines)
