from __future__ import division, print_function, absolute_import


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

class IdKey(object):

    def __repr__(self):
        return u'IdKey(%r)' % (self.value,)

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
