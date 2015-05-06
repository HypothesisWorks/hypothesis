# coding=utf-8

# Copyright (C) 2013-2015 David R. MacIver (david@drmaciver.com)

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

from __future__ import division, print_function, absolute_import, \
    unicode_literals

from contextlib import contextmanager

from hypothesis import find, given
from tests.common.utils import fails, capture_out
from hypothesis.settings import Settings, Verbosity
from hypothesis.reporting import default as default_reporter
from hypothesis.reporting import with_reporter
from hypothesis.searchstrategy import BasicStrategy


@contextmanager
def capture_verbosity(level):
    with capture_out() as o:
        with with_reporter(default_reporter):
            with Settings(verbosity=level):
                yield o


class SillyStrategy(BasicStrategy):

    def generate(self, random, parameter_value):
        return True

    def simplify(self, random, value):
        if value:
            yield False


def test_prints_intermediate_in_success():
    with capture_verbosity(Verbosity.verbose) as o:
        @given(booleans())
        def test_works(x):
            pass
        test_works()
    lines = o.getvalue().splitlines()
    assert len([l for l in lines if 'example' in l]) == 2


def test_reports_differently_for_single_shrink():
    with capture_verbosity(Verbosity.verbose) as o:
        @fails
        @given(SillyStrategy, settings=Settings(database=None))
        def test_foo(x):
            assert False
        test_foo()
    assert 'shrunk example once' in o.getvalue()


def test_reports_no_shrinks():
    with capture_verbosity(Verbosity.verbose) as o:
        @fails
        @given(())
        def test_foo(x):
            assert False
        test_foo()
    assert 'Could not shrink example' in o.getvalue()


def test_does_not_log_in_quiet_mode():
    with capture_verbosity(Verbosity.quiet) as o:
        @fails
        @given(integers())
        def test_foo(x):
            assert False

        test_foo()
    assert not o.getvalue()


def test_includes_progress_in_verbose_mode():
    with capture_verbosity(Verbosity.verbose) as o:
        with Settings(verbosity=Verbosity.verbose):
            find([int], lambda x: sum(x) >= 1000000)

    out = o.getvalue()
    assert out
    assert 'Shrunk example' in out
    assert 'Found satisfying example' in out


def test_prints_initial_attempts_on_find():

    with capture_verbosity(Verbosity.verbose) as o:
        with Settings(verbosity=Verbosity.verbose):
            seen = []

            def not_first(x):
                if not seen:
                    seen.append(x)
                    return False
                return x not in seen
            find(int, not_first)

    assert 'Trying example' in o.getvalue()


def test_includes_intermediate_results_in_verbose_mode():
    with capture_verbosity(Verbosity.verbose) as o:
        @fails
        @given([int])
        def test_foo(x):
            assert sum(x) < 1000000

        test_foo()
    lines = o.getvalue().splitlines()
    assert len([l for l in lines if 'example' in l]) > 2
    assert len([l for l in lines if 'AssertionError' in l])
