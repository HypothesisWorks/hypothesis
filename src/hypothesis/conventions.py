from __future__ import division, print_function, unicode_literals


# coding=utf-8

# Copyright (C) 2013-2015 David R. MacIver (david@drmaciver.com)

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

class UniqueIdentifier(object):

    def __init__(self, identifier):
        self.identifier = identifier

    def __repr__(self):
        return self.identifier


not_set = UniqueIdentifier('not_set')
