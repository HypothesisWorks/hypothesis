# coding=utf-8
#
# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)
#
# Most of this work is copyright (C) 2013-2015 David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
# https://github.com/DRMacIver/hypothesis/blob/master/CONTRIBUTING.rst for a
# full list of people who may hold copyright, and consult the git log if you
# need to determine who owns an individual contribution.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.
#
# END HEADER

from __future__ import division, print_function, absolute_import


def default_new_style_executor(data, function):
    return function(data)


class setup_teardown_executor(object):
    def __init__(self, setup, teardown):
        self.setup = setup
        self.teardown = teardown

    def __call__(self, data, function):
        try:
            if self.setup is not None:
                self.setup()
                return function(data)
        finally:
            if self.teardown is not None:
                self.teardown()



class TestRunner(object):

    def hypothesis_execute_example_with_data(self, data, function):
        return function(data)


def new_style_executor(runner):
    if runner is None:
        return default_new_style_executor
    if isinstance(runner, TestRunner):
        return runner.hypothesis_execute_example_with_data

    if (
        hasattr(runner, 'setup_example') or
        hasattr(runner, 'teardown_example')
    ):
        return setup_teardown_executor(
            getattr(runner, 'setup_example', None),
            getattr(runner, 'teardown_example', None),
        )
    return default_new_style_executor
