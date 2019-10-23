# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Most of this work is copyright (C) 2013-2019 David R. MacIver
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

from __future__ import absolute_import, division, print_function

from contextlib import contextmanager

from hypothesis import find, given
from hypothesis._settings import Verbosity, settings
from hypothesis.reporting import default as default_reporter, with_reporter
from hypothesis.strategies import booleans, integers, lists
from tests.common.debug import minimal
from tests.common.utils import capture_out, checks_deprecated_behaviour, fails


@contextmanager
def capture_verbosity():
    with capture_out() as o:
        with with_reporter(default_reporter):
            yield o


def test_prints_intermediate_in_success():
    with capture_verbosity() as o:

        @settings(verbosity=Verbosity.verbose)
        @given(booleans())
        def test_works(x):
            pass

        test_works()
    assert "Trying example" in o.getvalue()


def test_does_not_log_in_quiet_mode():
    with capture_verbosity() as o:

        @fails
        @settings(verbosity=Verbosity.quiet)
        @given(integers())
        def test_foo(x):
            assert False

        test_foo()
    assert not o.getvalue()


def test_includes_progress_in_verbose_mode():
    with capture_verbosity() as o:
        minimal(
            lists(integers(), min_size=1),
            lambda x: sum(x) >= 100,
            settings(verbosity=Verbosity.verbose),
        )
    out = o.getvalue()
    assert out
    assert u"Trying example: " in out
    assert u"Falsifying example: " in out


@checks_deprecated_behaviour
def test_prints_initial_attempts_on_find():

    with capture_verbosity() as o:

        def foo():
            seen = []

            def not_first(x):
                if not seen:
                    seen.append(x)
                    return False
                return x not in seen

            find(integers(), not_first, settings=settings(verbosity=Verbosity.verbose))

        foo()

    assert u"Tried non-satisfying example" in o.getvalue()


def test_includes_intermediate_results_in_verbose_mode():
    with capture_verbosity() as o:

        @fails
        @settings(verbosity=Verbosity.verbose, database=None, derandomize=True)
        @given(lists(integers(), min_size=1))
        def test_foo(x):
            assert sum(x) < 10000

        test_foo()
    lines = o.getvalue().splitlines()
    assert len([l for l in lines if u"example" in l]) > 2
    assert [l for l in lines if u"AssertionError" in l]
