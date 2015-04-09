# coding=utf-8

# Copyright (C) 2013-2015 David R. MacIver (david@drmaciver.com)

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

"""Package defining SearchStrategy, which is the core type that Hypothesis uses
to explore data."""

from __future__ import division, print_function, absolute_import, \
    unicode_literals

from .strategies import SearchStrategy, strategy
from .basic import BasicStrategy

from . import numbers as s1
from . import collections as s2
from . import strings as s3
from . import misc as s4
from . import streams as s5

# Placate flake8
loaded = [s1, s2, s3, s4, s5]


__all__ = [
    'strategy',
    'SearchStrategy',
    'BasicStrategy',
]
