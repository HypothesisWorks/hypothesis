# coding=utf-8

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# Most of this work is copyright (C) 2013-2015 David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
# https://github.com/DRMacIver/hypothesis/blob/master/CONTRIBUTING.rst for a
# full list of people who may hold copyright, and consult the git log if you
# need to determine who owns an individual contribution.

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

from __future__ import division, print_function, absolute_import

from hypothesis.utils.extmethod import ExtMethod

executor = ExtMethod()


def default_executor(function):
    return function()


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


@executor.extend(object)
def attr_based_executor(runner):
    try:
        return runner.execute_example
    except AttributeError:
        pass

    if (
        hasattr(runner, u'setup_example') or
        hasattr(runner, u'teardown_example')
    ):
        return setup_teardown_executor(
            getattr(runner, u'setup_example', None),
            getattr(runner, u'teardown_example', None),
        )

    return default_executor
