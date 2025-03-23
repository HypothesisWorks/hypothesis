# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

from contextlib import contextmanager

from hypothesis import example, find, given
from hypothesis._settings import Verbosity, settings
from hypothesis.reporting import default as default_reporter, with_reporter
from hypothesis.strategies import booleans, integers, lists

from tests.common.debug import minimal
from tests.common.utils import Why, capture_out, fails, xfail_on_crosshair


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
        @settings(verbosity=Verbosity.quiet, print_blob=False)
        @given(integers())
        def test_foo(x):
            raise AssertionError

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
    assert "Trying example: " in out


@xfail_on_crosshair(Why.symbolic_outside_context, strict=False)
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
                integers(),
                not_first,
                settings=settings(verbosity=Verbosity.verbose, max_examples=1000),
            )

        foo()

    assert "Trying example" in o.getvalue()


def test_includes_intermediate_results_in_verbose_mode():
    with capture_verbosity() as o:

        @fails
        @settings(
            verbosity=Verbosity.verbose,
            database=None,
            derandomize=True,
            max_examples=100,
        )
        @given(lists(integers(), min_size=1))
        def test_foo(x):
            assert sum(x) < 10000

        test_foo()
    lines = o.getvalue().splitlines()
    assert len([l for l in lines if "example" in l]) > 2
    assert [l for l in lines if "AssertionError" in l]


@example(0)
@settings(verbosity=Verbosity.quiet)
@given(integers())
def test_no_indexerror_in_quiet_mode(x):
    # Regression tests for https://github.com/HypothesisWorks/hypothesis/issues/2696
    # where quiet mode -> no fragments to report -> IndexError accessing first report
    pass


@fails
@example(0)
@settings(verbosity=Verbosity.quiet, report_multiple_bugs=True)
@given(integers())
def test_no_indexerror_in_quiet_mode_report_multiple(x):
    assert x


@fails
@example(0)
@settings(verbosity=Verbosity.quiet, report_multiple_bugs=False)
@given(integers())
def test_no_indexerror_in_quiet_mode_report_one(x):
    assert x
