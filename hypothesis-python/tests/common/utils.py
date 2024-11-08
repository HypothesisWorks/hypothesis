# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import contextlib
import sys
import warnings
from io import StringIO
from types import SimpleNamespace

from hypothesis import Phase, settings
from hypothesis.errors import HypothesisDeprecationWarning
from hypothesis.internal.entropy import deterministic_PRNG
from hypothesis.internal.floats import next_down
from hypothesis.internal.observability import TESTCASE_CALLBACKS
from hypothesis.internal.reflection import proxies
from hypothesis.reporting import default, with_reporter
from hypothesis.strategies._internal.core import from_type, register_type_strategy
from hypothesis.strategies._internal.types import _global_type_lookup

try:
    from pytest import raises
except ModuleNotFoundError:
    # We are currently running under a test framework other than pytest,
    # so use our own simplified implementation of `pytest.raises`.

    @contextlib.contextmanager
    def raises(expected_exception, match=None):
        err = SimpleNamespace(value=None)
        try:
            yield err
        except expected_exception as e:
            err.value = e
            if match is not None:
                import re

                assert re.search(match, e.args[0])
        else:
            # This needs to be outside the try/except, so that the helper doesn't
            # trick itself into thinking that an AssertionError was thrown.
            raise AssertionError(
                f"Expected to raise an exception ({expected_exception!r}) but didn't"
            ) from None


try:
    from pytest import mark
except ModuleNotFoundError:

    def skipif_emscripten(f):
        return f

else:
    skipif_emscripten = mark.skipif(
        sys.platform == "emscripten",
        reason="threads, processes, etc. are not available in the browser",
    )


no_shrink = tuple(set(settings.default.phases) - {Phase.shrink, Phase.explain})


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


def fails_with(e, *, match=None):
    def accepts(f):
        @proxies(f)
        def inverted_test(*arguments, **kwargs):
            # Most of these expected-failure tests are non-deterministic, so
            # we rig the PRNG to avoid occasional flakiness. We do this outside
            # the `raises` context manager so that any problems in rigging the
            # PRNG don't accidentally count as the expected failure.
            with deterministic_PRNG():
                with raises(e, match=match):
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
                f"Expected a deprecation warning but got {[e.category for e in w]!r}"
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
        assert f"{k}={v!r}" in output, (f"{k}={v!r}", output)


def assert_falsifying_output(
    test, example_type="Falsifying", expected_exception=AssertionError, **kwargs
):
    with capture_out() as out:
        if expected_exception is None:
            # Some tests want to check the output of non-failing runs.
            test()
            msg = ""
        else:
            with raises(expected_exception) as exc_info:
                test()
            notes = "\n".join(getattr(exc_info.value, "__notes__", []))
            msg = str(exc_info.value) + "\n" + notes

    output = out.getvalue() + msg
    assert f"{example_type} example:" in output
    assert_output_contains_failure(output, test, **kwargs)


@contextlib.contextmanager
def temp_registered(type_, strat_or_factory):
    """Register and un-register a type for st.from_type().

    This not too hard, but there's a subtlety in restoring the
    previously-registered strategy which we got wrong in a few places.
    """
    prev = _global_type_lookup.get(type_)
    register_type_strategy(type_, strat_or_factory)
    try:
        yield
    finally:
        del _global_type_lookup[type_]
        from_type.__clear_cache()
        if prev is not None:
            register_type_strategy(type_, prev)


@contextlib.contextmanager
def raises_warning(expected_warning, match=None):
    """Use instead of pytest.warns to check that the raised warning is handled properly"""
    with raises(expected_warning, match=match) as r:
        with warnings.catch_warnings():
            warnings.simplefilter("error", category=expected_warning)
            yield r


@contextlib.contextmanager
def capture_observations():
    ls = []
    TESTCASE_CALLBACKS.append(ls.append)
    try:
        yield ls
    finally:
        TESTCASE_CALLBACKS.remove(ls.append)


# Specifies whether we can represent subnormal floating point numbers.
# IEE-754 requires subnormal support, but it's often disabled anyway by unsafe
# compiler options like `-ffast-math`.  On most hardware that's even a global
# config option, so *linking against* something built this way can break us.
# Everything is terrible
PYTHON_FTZ = next_down(sys.float_info.min) == 0.0
