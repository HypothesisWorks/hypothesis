# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2017 David R. MacIver
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

from hypothesis._settings import note_deprecation


def default_executor(function):  # pragma: nocover
    raise NotImplementedError()  # We don't actually use this any more


def setup_teardown_executor(setup, teardown):
    setup = setup or (lambda: None)
    teardown = teardown or (lambda ex: None)

    def execute(function):
        token = None
        try:
            token = setup()
            return function()
        finally:
            teardown(token)
    return execute


def executor(runner):
    try:
        return runner.execute_example
    except AttributeError:
        pass

    if (
        hasattr(runner, 'setup_example') or
        hasattr(runner, 'teardown_example')
    ):
        return setup_teardown_executor(
            getattr(runner, 'setup_example', None),
            getattr(runner, 'teardown_example', None),
        )

    return default_executor


def default_new_style_executor(data, function):
    return function(data)


class ConjectureRunner(object):

    def hypothesis_execute_example_with_data(self, data, function):
        return function(data)


def new_style_executor(runner):
    if runner is None:
        return default_new_style_executor

    if isinstance(runner, ConjectureRunner):
        note_deprecation(
            'Use of the ConjectureRunner type is deprecated and will go away '
            'in Hypothesis 4.0. Use the new lifecycle hooks API instead.'
        )
        return runner.hypothesis_execute_example_with_data

    old_school = executor(runner)
    if old_school is default_executor:
        return default_new_style_executor
    else:
        if old_school is setup_teardown_executor:
            note_deprecation(
                'setup_example and teardown_example should be decorated with '
                '@lifecycle_hook. Use without is deprecated and will stop '
                'working in Hypothesis 4.0.'
            )
        else:
            note_deprecation(
                'The classic executor API is deprecated and will go away in '
                'Hypothesis 4.0. Use the new lifecycle hooks API instead. '
                "If you did not intend this to be an executor or don't know "
                'what that means, try decorating @given with @lifecycle(None).'
            )
        return lambda data, function: old_school(
            lambda: function(data)
        )
