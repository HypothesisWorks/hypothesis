# coding=utf-8
#
# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)
#
# Most of this work is copyright (C) 2013-2015 David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
# https://github.com/DRMacIver/hypothesis/blob/master/CONTRIBUTING.rst for a
# full list of people who may hold copyright, and consult the git log if you
# need to determine who owns an individual contribution.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.
#
# END HEADER

from __future__ import division, print_function, absolute_import

from hypothesis.control import current_build_context
from hypothesis.searchstrategy.wrappers import SearchStrategy


class SharedTemplate(object):

    def __init__(self, base):
        self.base = base
        self.used = False

    def __repr__(self):
        return 'SharedStrategy(%r, used=%r)' % (self.base, self.used)

    def __copy__(self):
        return SharedStrategy(self.base)

    def __trackas__(self):
        return self.base


SHARED_STRATEGY_ATTRIBUTE = '_hypothesis_shared_strategies'


class SharedStrategy(SearchStrategy):

    def __init__(self, base, key=None):
        self.key = key
        self.base = base

    def __repr__(self):
        if self.key is not None:
            return 'shared(%r, key=%r)' % (self.base, self.key)
        else:
            return 'shared(%r)' % (self.base,)

    def draw_parameter(self, random):
        return self.base.draw_parameter(random)

    def draw_template(self, random, pv):
        return SharedTemplate(self.base.draw_template(random, pv))

    def reify(self, value):
        context = current_build_context()
        if not hasattr(context, SHARED_STRATEGY_ATTRIBUTE):
            setattr(context, SHARED_STRATEGY_ATTRIBUTE, {})
        sharing = getattr(context, SHARED_STRATEGY_ATTRIBUTE)
        key = self.key or self
        if key in sharing:
            value.used = False
        else:
            value.used = True
            sharing[key] = self.base.reify(value.base)
        return sharing[key]

    def simplifiers(self, random, template):
        if template.used:
            for s in self.base.simplifiers(random, template.base):
                yield self.convert_simplifier(s)

    def convert_simplifier(self, simplifier):
        def accept(random, template):
            for b in simplifier(random, template.base):
                yield SharedTemplate(b)
        accept.__name__ = simplifier.__name__
        return accept

    def strictly_simpler(self, x, y):
        return self.base.strictly_simpler(x.base, y.base)

    def to_basic(self, template):
        return self.base.to_basic(template.base)

    def from_basic(self, data):
        return SharedTemplate(self.base.from_basic(data))
