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
from hypothesis.internal.compat import text_type, binary_type, \
    encoded_filepath


def belongs_to(package):
    root = os.path.dirname(package.__file__)
    cache = {text_type: {}, binary_type: {}}

    def accept(filepath):
        try:
            return cache[type(filepath)][filepath]
        except KeyError:
            pass
        filepath = encoded_filepath(filepath)
        result = os.path.abspath(filepath).startswith(root)
        cache[type(filepath)][filepath] = result
        return result
    accept.__name__ = 'is_%s_file' % (package.__name__,)
    return accept


PREVENT_ESCALATION = os.getenv('HYPOTHESIS_DO_NOT_ESCALATE') == 'true'

FILE_CACHE = {}


is_hypothesis_file = belongs_to(hypothesis)
is_coverage_file = belongs_to(coverage)


def escalate_hypothesis_internal_error():
    if PREVENT_ESCALATION:
        return
    error_type, _, tb = sys.exc_info()
    import traceback
    filepath = traceback.extract_tb(tb)[-1][0]
    if is_hypothesis_file(filepath) and not issubclass(
        error_type, DeadlineExceeded
    ):
        raise
    # This is so that if we do something wrong and trigger an internal Coverage
    # error we don't try to catch it. It should be impossible to trigger, but
    # you never know.
    if is_coverage_file(filepath):  # pragma: no cover
        raise
