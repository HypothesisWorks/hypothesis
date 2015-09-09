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

"""Package defining SearchStrategy, which is the core type that Hypothesis uses
to explore data."""


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
