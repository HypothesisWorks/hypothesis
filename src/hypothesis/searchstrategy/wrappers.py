# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2017 David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
# CONTRIBUTING.rst for a full list of people who may hold copyright, and
# consult the git log if you need to determine who owns an individual
# contribution.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.
#
# END HEADER

from __future__ import division, print_function, absolute_import

from hypothesis.searchstrategy.strategies import SearchStrategy


class WrapperStrategy(SearchStrategy):

    """A strategy which is defined purely by conversion to and from another
    strategy.

    Its parameter and distribution come from that other strategy.

    """

    def __init__(self, strategy):
        SearchStrategy.__init__(self)
        self.wrapped_strategy = strategy

    @property
    def supports_find(self):
        return self.wrapped_strategy.supports_find

    @property
    def is_empty(self):
        return self.wrapped_strategy.is_empty

    def __repr__(self):
        return u'%s(%r)' % (type(self).__name__, self.wrapped_strategy)

    def validate(self):
        self.wrapped_strategy.validate()

    def do_draw(self, data):
        return self.wrapped_strategy.do_draw(data)
