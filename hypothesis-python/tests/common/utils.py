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

import contextlib
import sys
import traceback
from io import StringIO

from hypothesis._settings import Phase
from hypothesis.errors import HypothesisDeprecationWarning
from hypothesis.internal.reflection import proxies
from hypothesis.reporting import default, with_reporter
from hypothesis.strategies._internal.core import from_type, register_type_strategy
from hypothesis.strategies._internal.types import _global_type_lookup

no_shrink = tuple(set(Phase) - {Phase.shrink})


def flaky(max_runs, min_passes):
    assert isinstance(max_runs, int)
    assert isinstance(min_passes, int)
    assert 0 < min_passes <= max_runs <= 50  # arbitrary cap

    def accept(func):
        @proxies(func)
        def inner(*args, **kwargs):
            runs = passes = 0
            while passes < min_passes:
                runs += 1
                try:
                    func(*args, **kwargs)
                    passes += 1
                except BaseException:
                    if runs >= max_runs:
                        raise

        return inner

    return accept


@contextlib.contextmanager
def capture_out():
    old_out = sys.stdout
    try:
        new_out = StringIO()
        sys.stdout = new_out
        with with_reporter(default):
            yield new_out
    finally:
        sys.stdout = old_out


class ExcInfo:
    pass


@contextlib.contextmanager
def raises(exctype):
    e = ExcInfo()
    try:
        yield e
        assert False, "Expected to raise an exception but didn't"
    except exctype as err:
        traceback.print_exc()
        e.value = err
        return


def fails_with(e):
    def accepts(f):
        @proxies(f)
        def inverted_test(*arguments, **kwargs):
            with raises(e):
                f(*arguments, **kwargs)

        return inverted_test

    return accepts


fails = fails_with(AssertionError)


class NotDeprecated(Exception):
    pass


@contextlib.contextmanager
def validate_deprecation():
    import warnings

    try:
        warnings.simplefilter("always", HypothesisDeprecationWarning)
        with warnings.catch_warnings(record=True) as w:
            yield
    finally:
        warnings.simplefilter("error", HypothesisDeprecationWarning)
        if not any(e.category == HypothesisDeprecationWarning for e in w):
            raise NotDeprecated(
                "Expected to get a deprecation warning but got %r"
                % ([e.category for e in w],)
            )


def checks_deprecated_behaviour(func):
    """A decorator for testing deprecated behaviour."""

    @proxies(func)
    def _inner(*args, **kwargs):
        with validate_deprecation():
            return func(*args, **kwargs)

    return _inner


def all_values(db):
    return {v for vs in db.data.values() for v in vs}


def non_covering_examples(database):
    return {
        v for k, vs in database.data.items() if not k.endswith(b".pareto") for v in vs
    }


def counts_calls(func):
    """A decorator that counts how many times a function was called, and
    stores that value in a ``.calls`` attribute.
    """
    assert not hasattr(func, "calls")

    @proxies(func)
    def _inner(*args, **kwargs):
        _inner.calls += 1
        return func(*args, **kwargs)

    _inner.calls = 0
    return _inner


def assert_output_contains_failure(output, test, **kwargs):
    assert test.__name__ + "(" in output
    for k, v in kwargs.items():
        assert ("%s=%r" % (k, v)) in output


def assert_falsifying_output(
    test, example_type="Falsifying", expected_exception=AssertionError, **kwargs
):
    with capture_out() as out:
        with raises(expected_exception):
            test()

    assert "%s example:" % (example_type,)
    assert_output_contains_failure(out.getvalue(), test, **kwargs)


@contextlib.contextmanager
def temp_registered(type_, strat_or_factory):
    """Register and un-register a type for st.from_type().

    This not too hard, but there's a subtlety in restoring the
    previously-registered strategy which we got wrong in a few places.
    """
    prev = _global_type_lookup.get(type_)
    try:
        register_type_strategy(type_, strat_or_factory)
        yield
    finally:
        del _global_type_lookup[type_]
        from_type.__clear_cache()
        if prev is not None:
            register_type_strategy(type_, prev)
