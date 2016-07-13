# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2015 David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
# CONTRIBUTING.rst for a full list of people who may hold copyright, and
# consult the git log if you need to determine who owns an individual
# contribution.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.
#
# END HEADER

from __future__ import division, print_function, absolute_import

from contextlib import contextmanager

import pytest

from hypothesis import find, given
from hypothesis.errors import InvalidArgument
from tests.common.utils import fails, capture_out
from hypothesis._settings import settings, Verbosity
from hypothesis.reporting import default as default_reporter
from hypothesis.reporting import with_reporter
from hypothesis.strategies import lists, booleans, integers


@contextmanager
def capture_verbosity(level):
    with capture_out() as o:
        with with_reporter(default_reporter):
            with settings(verbosity=level):
                yield o


def test_prints_intermediate_in_success():
    with capture_verbosity(Verbosity.verbose) as o:
        @given(booleans())
        def test_works(x):
            pass
        test_works()
    assert 'Trying example' in o.getvalue()


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
        with settings(verbosity=Verbosity.verbose):
            find(lists(integers()), lambda x: sum(x) >= 1000000)

    out = o.getvalue()
    assert out
    assert u'Shrunk example' in out
    assert u'Found satisfying example' in out


def test_prints_initial_attempts_on_find():

    with capture_verbosity(Verbosity.verbose) as o:
        with settings(verbosity=Verbosity.verbose):
            seen = []

            def not_first(x):
                if not seen:
                    seen.append(x)
                    return False
                return x not in seen
            find(integers(), not_first)

    assert u'Trying example' in o.getvalue()


def test_includes_intermediate_results_in_verbose_mode():
    with capture_verbosity(Verbosity.verbose) as o:
        @fails
        @given(lists(integers()))
        def test_foo(x):
            assert sum(x) < 1000000

        test_foo()
    lines = o.getvalue().splitlines()
    assert len([l for l in lines if u'example' in l]) > 2
    assert len([l for l in lines if u'AssertionError' in l])


VERBOSITIES = [
    Verbosity.quiet, Verbosity.normal, Verbosity.verbose, Verbosity.debug
]


def test_verbosity_can_be_accessed_by_name():
    for f in VERBOSITIES:
        assert f is Verbosity.by_name(f.name)


def test_verbosity_is_sorted():
    assert VERBOSITIES == sorted(VERBOSITIES)


def test_hash_verbosity():
    x = {}
    for f in VERBOSITIES:
        x[f] = f
    for k, v in x.items():
        assert k == v
        assert k is v


def test_verbosities_are_inequal():
    for f in VERBOSITIES:
        for g in VERBOSITIES:
            if f is not g:
                assert f != g
                assert (f <= g) or (g <= f)


def test_verbosity_of_bad_name():
    with pytest.raises(InvalidArgument):
        Verbosity.by_name('cabbage')
