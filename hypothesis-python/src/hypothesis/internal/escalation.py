# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2018 David R. MacIver
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

import hypothesis
from hypothesis.errors import StopTest, DeadlineExceeded, \
    HypothesisException, UnsatisfiedAssumption
from hypothesis.internal.compat import text_type, binary_type, \
    encoded_filepath

if False:
    from typing import Dict  # noqa


def belongs_to(package):
    root = os.path.dirname(package.__file__)
    cache = {text_type: {}, binary_type: {}}

    def accept(filepath):
        ftype = type(filepath)
        try:
            return cache[ftype][filepath]
        except KeyError:
            pass
        new_filepath = encoded_filepath(filepath)
        result = os.path.abspath(new_filepath).startswith(root)
        cache[ftype][filepath] = result
        cache[type(new_filepath)][new_filepath] = result
        return result
    accept.__name__ = 'is_%s_file' % (package.__name__,)
    return accept


PREVENT_ESCALATION = os.getenv('HYPOTHESIS_DO_NOT_ESCALATE') == 'true'

FILE_CACHE = {}  # type: Dict[bytes, bool]


is_hypothesis_file = belongs_to(hypothesis)

HYPOTHESIS_CONTROL_EXCEPTIONS = (
    DeadlineExceeded, StopTest, UnsatisfiedAssumption
)


def mark_for_escalation(e):
    if not isinstance(e, HYPOTHESIS_CONTROL_EXCEPTIONS):
        e.hypothesis_internal_always_escalate = True


def escalate_hypothesis_internal_error():
    if PREVENT_ESCALATION:
        return
    error_type, e, tb = sys.exc_info()
    if getattr(e, 'hypothesis_internal_always_escalate', False):
        raise
    import traceback
    filepath = traceback.extract_tb(tb)[-1][0]
    if is_hypothesis_file(filepath) and not isinstance(
        e, (HypothesisException,) + HYPOTHESIS_CONTROL_EXCEPTIONS,
    ):
        raise
