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

import inspect

from hypothesis.settings import Settings, Verbosity
from hypothesis.internal.compat import text_type
from hypothesis.utils.dynamicvariables import DynamicVariable


def silent(value):
    pass


def default(value):
    print(value)


reporter = DynamicVariable(default)


def current_reporter():
    return reporter.value


def with_reporter(new_reporter):
    return reporter.with_value(new_reporter)


def current_verbosity():
    return Settings.default.verbosity


def to_text(textish):
    if inspect.isfunction(textish):
        textish = textish()
    return text_type(textish)


def verbose_report(text):
    if current_verbosity() >= Verbosity.verbose:
        current_reporter()(to_text(text))


def debug_report(text):
    if current_verbosity() >= Verbosity.debug:
        current_reporter()(to_text(text))


def report(text):
    if current_verbosity() >= Verbosity.normal:
        current_reporter()(to_text(text))
