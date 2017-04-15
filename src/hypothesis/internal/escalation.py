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

INTERNAL_PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))
HYPOTHESIS_ROOT = os.path.dirname(INTERNAL_PACKAGE_DIR)

FILE_CACHE = {}


def is_hypothesis_file(filepath):
    try:
        return FILE_CACHE[filepath]
    except KeyError:
        pass
    result = os.path.abspath(filepath).startswith(HYPOTHESIS_ROOT)
    FILE_CACHE[filepath] = result
    return result


def escalate_hypothesis_internal_error():
    error_type, _, tb = sys.exc_info()
    import traceback
    filepath = traceback.extract_tb(tb)[-1][0]
    if is_hypothesis_file(filepath):
        raise
