# coding=utf-8
#
# This file is part of Hypothesis (https://github.com/HypothesisWorks/hypothesis-python)
#
# Most of this work is copyright (C) 2013-2015 David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
# https://github.com/HypothesisWorks/hypothesis-python/blob/master/CONTRIBUTING.rst for a
# full list of people who may hold copyright, and consult the git log if you
# need to determine who owns an individual contribution.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.
#
# END HEADER

from __future__ import division, print_function, absolute_import

from hypothesis.searchstrategy.wrappers import SearchStrategy

SHARED_STRATEGY_ATTRIBUTE = '_hypothesis_shared_strategies'


class SharedStrategy(SearchStrategy):

    def __init__(self, base, key=None):
        self.key = key
        self.base = base

    @property
    def supports_find(self):
        return self.base.supports_find

    def __repr__(self):
        if self.key is not None:
            return 'shared(%r, key=%r)' % (self.base, self.key)
        else:
            return 'shared(%r)' % (self.base,)

    def do_draw(self, data):
        if not hasattr(data, SHARED_STRATEGY_ATTRIBUTE):
            setattr(data, SHARED_STRATEGY_ATTRIBUTE, {})
        sharing = getattr(data, SHARED_STRATEGY_ATTRIBUTE)
        key = self.key or self
        if key not in sharing:
            sharing[key] = self.base.do_draw(data)
        return sharing[key]
