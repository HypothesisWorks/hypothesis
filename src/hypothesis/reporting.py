# coding=utf-8

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

from __future__ import print_function, unicode_literals

# END HEADER

from __future__ import unicode_literals, print_function

from hypothesis.internal.dynamicvariables import DynamicVariable


def silent(value):
    pass


def default(value):
    print(value)


reporter = DynamicVariable(default)


def current_reporter():
    return reporter.value


def with_reporter(new_reporter):
    return reporter.with_value(new_reporter)
