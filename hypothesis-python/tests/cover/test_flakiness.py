# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import sys

import pytest

from hypothesis import HealthCheck, Verbosity, assume, example, given, reject, settings
from hypothesis.core import StateForActualGivenExecution
from hypothesis.errors import Flaky, FlakyFailure, Unsatisfiable, UnsatisfiedAssumption
from hypothesis.internal.compat import ExceptionGroup
from hypothesis.internal.conjecture.engine import MIN_TEST_CALLS
from hypothesis.internal.scrutineer import Tracer
from hypothesis.strategies import booleans, composite, integers, lists, random_module

from tests.common.utils import Why, no_shrink, xfail_on_crosshair


class Nope(Exception):
    pass


def test_fails_only_once_is_flaky():
    first_call = True

    @given(integers())
    def rude(x):
        nonlocal first_call
        if first_call:
            first_call = False
            raise Nope

    with pytest.raises(FlakyFailure, match="Falsified on the first call but") as e:
        rude()
    exceptions = e.value.exceptions
    assert len(exceptions) == 1
    assert isinstance(exceptions[0], Nope)


def test_fails_differently_is_flaky():
    call_count = 0

    class DifferentNope(Exception):
        pass

    @given(integers())
    @settings(database=None)
    def rude(x):
        nonlocal call_count
        if x == 0:
            call_count += 1
            if call_count > 1:
                raise Nope
            else:
                raise DifferentNope

    with pytest.raises(FlakyFailure, match="Inconsistent results from replaying") as e:
        rude()
    exceptions = e.value.exceptions
    assert len(exceptions) == 2
    assert set(map(type, exceptions)) == {Nope, DifferentNope}


@pytest.mark.skipif(sys.version_info < (3, 11), reason="except* syntax")
def test_exceptiongroup_wrapped_naked_exception_is_flaky():

    # Defer parsing until runtime, as "except*" is syntax error pre 3.11
    rude_def = """
first_call = True
def rude_fn(x):
    global first_call
    if first_call:
        first_call = False
        try:
            raise Nope
        except* Nope:
            raise
    """
    exec(rude_def, globals())
    rude = given(integers())(rude_fn)  # noqa: F821 # defined by exec()

    with pytest.raises(FlakyFailure, match="Falsified on the first call but") as e:
        rude()
    exceptions = e.value.exceptions
    assert list(map(type, exceptions)) == [ExceptionGroup]
    assert list(map(type, exceptions[0].exceptions)) == [Nope]


def test_gives_flaky_error_if_assumption_is_flaky():
    seen = set()

    @given(integers())
    @settings(verbosity=Verbosity.quiet, database=None)
    def oops(s):
        assume(s not in seen)
        seen.add(s)
        raise AssertionError

    with pytest.raises(FlakyFailure, match="Inconsistent results from replaying") as e:
        oops()
    exceptions = e.value.exceptions
    assert len(exceptions) == 2
    assert isinstance(exceptions[0], AssertionError)
    assert isinstance(exceptions[1], UnsatisfiedAssumption)


def test_flaky_with_context_when_fails_only_under_tracing(monkeypatch):
    # make anything fail under tracing
    monkeypatch.setattr(Tracer, "can_trace", staticmethod(lambda: True))
    monkeypatch.setattr(Tracer, "__enter__", lambda *_: 1 / 0)
    # ensure tracing is always entered inside _execute_once_for_engine
    monkeypatch.setattr(StateForActualGivenExecution, "_should_trace", lambda _: True)

    @given(integers())
    def test(x):
        pass

    with pytest.raises(
        FlakyFailure, match="failed on the first run but now succeeds"
    ) as e:
        test()
    exceptions = e.value.exceptions
    assert len(exceptions) == 1
    assert isinstance(exceptions[0], ZeroDivisionError)


@xfail_on_crosshair(Why.symbolic_outside_context)
def test_does_not_attempt_to_shrink_flaky_errors():
    values = []

    @settings(database=None)
    @given(integers())
    def test(x):
        values.append(x)
        assert len(values) != 1

    with pytest.raises(FlakyFailure):
        test()
    # We try a total of ten calls in the generation phase, each usually a
    # unique value, looking briefly (and unsuccessfully) for another bug.
    assert 1 < len(set(values)) <= MIN_TEST_CALLS
    # We don't try any new values while shrinking, just execute the test
    # twice more (to check for flakiness and to raise the bug to the user).
    assert set(values) == set(values[:-2])


class SatisfyMe(Exception):
    pass


@composite
def single_bool_lists(draw):
    n = draw(integers(0, 20))
    result = [False] * (n + 1)
    result[n] = True
    return result


@xfail_on_crosshair(Why.nested_given)
@example([True, False, False, False], [3], None)
@example([False, True, False, False], [3], None)
@example([False, False, True, False], [3], None)
@example([False, False, False, True], [3], None)
@settings(deadline=None, suppress_health_check=[HealthCheck.nested_given])
@given(lists(booleans()) | single_bool_lists(), lists(integers(1, 3)), random_module())
def test_failure_sequence_inducing(building, testing, rnd):
    buildit = iter(building)
    testit = iter(testing)

    def build(x):
        try:
            assume(not next(buildit))
        except StopIteration:
            pass
        return x

    @given(integers().map(build))
    @settings(
        verbosity=Verbosity.quiet,
        database=None,
        suppress_health_check=list(HealthCheck),
        phases=no_shrink,
    )
    def test(x):
        try:
            i = next(testit)
        except StopIteration:
            return
        if i == 1:
            return
        elif i == 2:
            reject()
        else:
            raise Nope

    try:
        test()
    except (Nope, Flaky, Unsatisfiable):
        pass
    except UnsatisfiedAssumption:
        raise SatisfyMe from None
