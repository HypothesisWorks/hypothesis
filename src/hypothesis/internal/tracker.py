# coding=utf-8

# Copyright (C) 2013-2015 David R. MacIver (david@drmaciver.com)

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

from __future__ import division, print_function, absolute_import, \
    unicode_literals

import hashlib
import collections

import marshal
from hypothesis.internal.compat import text_type, binary_type


def flatten(x):
    if isinstance(x, (text_type, binary_type)):
        return x
    if isinstance(x, collections.Mapping):
        return (type(x).__name__, tuple(map(flatten, x.items())))
    if isinstance(x, collections.Iterable):
        return (type(x).__name__, tuple(map(flatten, x)))
    return x


def object_to_tracking_key(o):
    k = marshal.dumps(flatten(o))

    if len(k) < 20:
        return k
    else:
        return hashlib.sha1(k).digest()


class Tracker(object):

    def __init__(self):
        self.contents = set()

    def __len__(self):
        return len(self.contents)

    def track(self, x):
        k = object_to_tracking_key(x)
        if k in self.contents:
            return 2
        else:
            self.contents.add(k)
            return 1
