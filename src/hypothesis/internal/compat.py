# coding=utf-8

# Copyright (C) 2013-2015 David R. MacIver (david@drmaciver.com)

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

# pylint: skip-file
from __future__ import division, print_function, absolute_import, \
    unicode_literals

import sys
import importlib

PY3 = sys.version_info[0] == 3

if PY3:
    text_type = str
    binary_type = bytes
    hrange = range
    ARG_NAME_ATTRIBUTE = 'arg'
    integer_types = (int,)
    hunichr = chr
    from functools import reduce
else:
    text_type = unicode
    binary_type = str

    def hrange(start_or_finish, finish=None, step=None):
        try:
            if step is None:
                if finish is None:
                    return xrange(start_or_finish)
                else:
                    return xrange(start_or_finish, finish)
            else:
                return xrange(start_or_finish, finish, step)
        except OverflowError:
            if step == 0:
                raise ValueError('step argument may not be zero')
            if step is None:
                step = 1
            if finish is not None:
                start = start_or_finish
            else:
                start = 0
                finish = start_or_finish
            assert step != 0
            if step > 0:
                def shimrange():
                    i = start
                    while i < finish:
                        yield i
                        i += step
            else:
                def shimrange():
                    i = start
                    while i > finish:
                        yield i
                        i += step
            return shimrange()

    ARG_NAME_ATTRIBUTE = 'id'
    integer_types = (int, long)
    hunichr = unichr
    reduce = reduce

importlib_invalidate_caches = getattr(
    importlib, 'invalidate_caches', lambda: ())
