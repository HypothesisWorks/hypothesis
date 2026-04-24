# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import functools
import inspect

from hypothesis import Phase, given, settings

from tests.common.utils import run_test_for_falsifying_example

SNAPSHOT_SETTINGS = settings(
    phases=[Phase.generate, Phase.shrink],
    print_blob=False,
    derandomize=True,
    database=None,
)

EXPLAIN_SETTINGS = settings(
    phases=[Phase.generate, Phase.shrink, Phase.explain],
    print_blob=False,
    derandomize=True,
    database=None,
)


def snapshot_given(*strategies, **kwarg_strategies):
    """Decorator that turns the wrapped body into a pytest test: runs it as
    a Hypothesis property test and asserts that the captured
    falsifying-example output equals the ``snapshot`` fixture value.

    The body is expected to ``raise`` (e.g. ``AssertionError``) so the test
    has a falsifying example to report. ``EXPLAIN_SETTINGS`` is used so
    ``# or any other generated value``-style annotations participate in
    the snapshot.
    """

    def decorator(body):
        @functools.wraps(body)
        def prop_body(*args, **kwargs):
            body(*args, **kwargs)

        prop_body.__signature__ = inspect.signature(body)
        prop_test = given(*strategies, **kwarg_strategies)(EXPLAIN_SETTINGS(prop_body))

        def test_function(snapshot):
            assert run_test_for_falsifying_example(prop_test) == snapshot

        test_function.__name__ = body.__name__
        test_function.__qualname__ = body.__qualname__
        return test_function

    return decorator
