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

import os
import sys

import coverage
import hypothesis
from hypothesis.errors import DeadlineExceeded


def belongs_to(package):
    root = os.path.dirname(package.__file__)
    cache = {}

    def accept(filepath):
        try:
            return cache[filepath]
        except KeyError:
            pass
        result = os.path.abspath(filepath).startswith(root)
        cache[filepath] = result
        return result
    accept.__name__ = 'is_%s_file' % (package.__name__,)
    return accept


is_hypothesis_file = belongs_to(hypothesis)
is_coverage_file = belongs_to(coverage)


def escalate_hypothesis_internal_error():
    error_type, _, tb = sys.exc_info()
    import traceback
    filepath = traceback.extract_tb(tb)[-1][0]
    if is_hypothesis_file(filepath) and not issubclass(
        error_type, DeadlineExceeded
    ):
        raise
    if is_coverage_file(filepath) and issubclass(error_type, AssertionError):
        raise
