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

import traceback

from hypothesis import Verbosity, settings
from hypothesis.errors import CleanupFailed, InvalidArgument, UnsatisfiedAssumption
from hypothesis.reporting import report
from hypothesis.utils.dynamicvariables import DynamicVariable

if False:
    from typing import Any, AnyStr  # noqa


def reject():
    raise UnsatisfiedAssumption()


def assume(condition):
    # type: (Any) -> bool
    """Calling ``assume`` is like an :ref:`assert <python:assert>` that marks
    the example as bad, rather than failing the test.

    This allows you to specify properties that you *assume* will be
    true, and let Hypothesis try to avoid similar examples in future.
    """
    if not condition:
        raise UnsatisfiedAssumption()
    return True


_current_build_context = DynamicVariable(None)


def current_build_context():
    context = _current_build_context.value
    if context is None:
        raise InvalidArgument(u"No build context registered")
    return context


class BuildContext(object):
    def __init__(self, data, is_final=False, close_on_capture=True):
        self.data = data
        self.tasks = []
        self.is_final = is_final
        self.close_on_capture = close_on_capture
        self.close_on_del = False
        self.notes = []

    def __enter__(self):
        self.assign_variable = _current_build_context.with_value(self)
        self.assign_variable.__enter__()
        return self

    def __exit__(self, exc_type, exc_value, tb):
        self.assign_variable.__exit__(exc_type, exc_value, tb)
        if self.close() and exc_type is None:
            raise CleanupFailed()

    def close(self):
        any_failed = False
        for task in self.tasks:
            try:
                task()
            except BaseException:
                any_failed = True
                report(traceback.format_exc())
        return any_failed


def cleanup(teardown):
    """Register a function to be called when the current test has finished
    executing. Any exceptions thrown in teardown will be printed but not
    rethrown.

    Inside a test this isn't very interesting, because you can just use
    a finally block, but note that you can use this inside map, flatmap,
    etc. in order to e.g. insist that a value is closed at the end.
    """
    context = _current_build_context.value
    if context is None:
        raise InvalidArgument(u"Cannot register cleanup outside of build context")
    context.tasks.append(teardown)


def note(value):
    # type: (AnyStr) -> None
    """Report this value in the final execution."""
    context = _current_build_context.value
    if context is None:
        raise InvalidArgument("Cannot make notes outside of a test")
    context.notes.append(value)
    if context.is_final or settings.default.verbosity >= Verbosity.verbose:
        report(value)


def event(value):
    # type: (AnyStr) -> None
    """Record an event that occurred this test. Statistics on number of test
    runs with each event will be reported at the end if you run Hypothesis in
    statistics reporting mode.

    Events should be strings or convertible to them.
    """
    context = _current_build_context.value
    if context is None:
        raise InvalidArgument("Cannot make record events outside of a test")

    if context.data is not None:
        context.data.note_event(value)
