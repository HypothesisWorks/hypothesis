# coding=utf-8

# Copyright (C) 2013-2015 David R. MacIver (david@drmaciver.com)

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

from __future__ import division, print_function, unicode_literals

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
