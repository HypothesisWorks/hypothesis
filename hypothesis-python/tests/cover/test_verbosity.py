# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2018 David R. MacIver
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

import os
import sys
import subprocess
from contextlib import contextmanager

from hypothesis import find, given
from tests.common.utils import fails, capture_out
from hypothesis._settings import Verbosity, settings
from hypothesis.reporting import default as default_reporter
from hypothesis.reporting import with_reporter
from hypothesis.strategies import lists, booleans, integers


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
    assert 'Trying example' in o.getvalue()


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
        def foo():
            find(
                lists(integers()),
                lambda x: sum(x) >= 100,
                settings=settings(verbosity=Verbosity.verbose, database=None))

        foo()

    out = o.getvalue()
    assert out
    assert u'Shrunk example' in out
    assert u'Found satisfying example' in out


def test_prints_initial_attempts_on_find():

    with capture_verbosity() as o:
        def foo():
            seen = []

            def not_first(x):
                if not seen:
                    seen.append(x)
                    return False
                return x not in seen
            find(
                integers(), not_first,
                settings=settings(verbosity=Verbosity.verbose))

        foo()

    assert u'Tried non-satisfying example' in o.getvalue()


def test_includes_intermediate_results_in_verbose_mode():
    with capture_verbosity() as o:
        @fails
        @settings(verbosity=Verbosity.verbose, database=None)
        @given(lists(integers(), min_size=1))
        def test_foo(x):
            assert sum(x) < 1000000

        test_foo()
    lines = o.getvalue().splitlines()
    assert len([l for l in lines if u'example' in l]) > 2
    assert [l for l in lines if u'AssertionError' in l]


PRINT_VERBOSITY = """
from __future__ import print_function

import warnings
warnings.resetwarnings()

from hypothesis import settings

if __name__ == '__main__':
    print("VERBOSITY=%s" % (settings.default.verbosity.name,))
"""


def test_picks_up_verbosity_from_environment(tmpdir):
    script = tmpdir.join('printdebug.py')
    script.write(PRINT_VERBOSITY)
    environ = dict(os.environ)

    environ['HYPOTHESIS_VERBOSITY_LEVEL'] = 'debug'
    output = subprocess.check_output([
        sys.executable, str(script)
    ], env=environ).decode('ascii')

    assert 'VERBOSITY=debug' in output
