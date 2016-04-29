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

import traceback

from hypothesis.errors import CleanupFailed, InvalidArgument, \
    UnsatisfiedAssumption
from hypothesis.reporting import report
from hypothesis.utils.dynamicvariables import DynamicVariable


def reject():
    raise UnsatisfiedAssumption()


def assume(condition):
    """Assert a precondition for this test.

    If this is not truthy then the test will abort but not fail and
    Hypothesis will make a "best effort" attempt to avoid similar
    examples in future.

    """
    if not condition:
        raise UnsatisfiedAssumption()
    return True


_current_build_context = DynamicVariable(None)


def current_build_context():
    context = _current_build_context.value
    if context is None:
        raise InvalidArgument(
            u'No build context registered')
    return context


class BuildContext(object):

    def __init__(self, is_final=False, close_on_capture=True):
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

    def local(self):
        return _current_build_context.with_value(self)

    def close(self):
        any_failed = False
        for task in self.tasks:
            try:
                task()
            except:
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
        raise InvalidArgument(
            u'Cannot register cleanup outside of build context')
    context.tasks.append(teardown)


def note(value):
    """Report this value in the final execution.

    Will always call string conversion function of the value even if not
    printing for consistency of execution

    """
    context = _current_build_context.value
    if context is None:
        raise InvalidArgument(
            'Cannot make notes outside of build context')
    context.notes.append(value)
    if context.is_final:
        report(value)
