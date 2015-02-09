# coding=utf-8

# Copyright (C) 2013-2015 David R. MacIver (david@drmaciver.com)

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

""""external" methods.

They're still single dispatch but are not defined on the class.

"""

from __future__ import division, print_function, unicode_literals

from hypothesis.internal.classmap import ClassMap


class ExtMethod(object):

    def __init__(self):
        self.mapping = ClassMap()

    def extend(self, typ):
        def accept(f):
            self.mapping[typ] = f
            return f

        return accept

    def typekey(self, arg):
        return type(arg)

    def __call__(self, dispatch_arg, *args, **kwargs):
        typekey = self.typekey(dispatch_arg)
        try:
            f = self.mapping[typekey]
        except KeyError:
            raise NotImplementedError(
                'No implementation available for %s' % (typekey.__name__,)
            )
        return f(dispatch_arg, *args, **kwargs)
