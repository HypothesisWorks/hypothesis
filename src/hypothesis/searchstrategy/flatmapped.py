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

from hypothesis.internal.reflection import get_pretty_function_description
from hypothesis.searchstrategy.strategies import SearchStrategy


class FlatMapStrategy(SearchStrategy):

    def __init__(
        self, strategy, expand
    ):
        super(FlatMapStrategy, self).__init__()
        self.flatmapped_strategy = strategy
        self.expand = expand
        self.is_empty = strategy.is_empty

    def __repr__(self):
        if not hasattr(self, u'_cached_repr'):
            self._cached_repr = u'%r.flatmap(%s)' % (
                self.flatmapped_strategy, get_pretty_function_description(
                    self.expand))
        return self._cached_repr

    def do_draw(self, data):
        source = data.draw(self.flatmapped_strategy)
        data.mark_bind()
        return data.draw(self.expand(source))

    @property
    def branches(self):
        return [
            FlatMapStrategy(strategy=strategy, expand=self.expand)
            for strategy in self.flatmapped_strategy.branches
        ]
