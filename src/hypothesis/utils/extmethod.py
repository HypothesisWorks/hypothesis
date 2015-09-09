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

""""external" methods.

They're still single dispatch but are not defined on the class.

"""


from __future__ import division, print_function, absolute_import

from hypothesis.internal.classmap import ClassMap


class ExtMethod(object):

    def __init__(self):
        self.mapping = ClassMap()
        self.static_mapping = ClassMap()

    def extend(self, typ):
        def accept(f):
            self.mapping[typ] = f
            return f

        return accept

    def extend_static(self, typ):
        def accept(f):
            self.static_mapping[typ] = f
            return f

        return accept

    def __call__(self, dispatch_arg, *args, **kwargs):
        is_instance = True
        if isinstance(dispatch_arg, type):
            try:
                f = self.static_mapping[dispatch_arg]
                is_instance = False
            except KeyError:
                pass
        if is_instance:
            try:
                f = self.mapping[type(dispatch_arg)]
            except KeyError:
                raise NotImplementedError(
                    u'No implementation available for %r' % (
                        dispatch_arg,))
        return f(dispatch_arg, *args, **kwargs)
