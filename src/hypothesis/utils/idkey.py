# coding=utf-8

# Copyright (C) 2013-2015 David R. MacIver (david@drmaciver.com)

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

from __future__ import division, print_function, absolute_import, \
    unicode_literals


class IdKey(object):

    def __init__(self, value):
        self.value = value

    def __eq__(self, other):
        return (type(other) == IdKey) and (self.value is other.value)

    def __ne__(self, other):
        return not (self.__eq__(other))

    def __hash__(self):
        return hash(id(self.value))


class IdentitySet(object):

    def __init__(self):
        self.data = {}

    def __contains__(self, value):
        key = IdKey(value)
        return self.data.get(key, 0) > 0

    def add(self, value):
        key = IdKey(value)
        self.data[key] = self.data.get(key, 0) + 1

    def remove(self, value):
        key = IdKey(value)
        self.data[key] = self.data.get(key, 0) - 1
