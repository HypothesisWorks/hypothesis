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

TEST_DECORATORS_ALONE = """
import hypothesis
from hypothesis.strategies import composite

@composite
def test_composite_is_not_a_test(draw):
    # This strategy will be instantiated, but no draws == no calls.
    assert False

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
    testdir.runpytest(script).assert_outcomes(failed=4)
