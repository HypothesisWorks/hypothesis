# coding=utf-8

# Copyright (C) 2013-2015 David R. MacIver (david@drmaciver.com)

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

# pylint: skip-file
from __future__ import division, print_function, unicode_literals

import sys

PY3 = sys.version_info[0] == 3

if PY3:
    text_type = str
    binary_type = bytes
    hrange = range
    ARG_NAME_ATTRIBUTE = 'arg'
    integer_types = (int,)
    hunichr = chr
else:
    text_type = unicode
    binary_type = str
    from __builtin__ import xrange as hrange
    ARG_NAME_ATTRIBUTE = 'id'
    integer_types = (int, long)
    hunichr = unichr
