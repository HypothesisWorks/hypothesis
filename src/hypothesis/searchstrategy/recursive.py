# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2015 David R. MacIver
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

from contextlib import contextmanager

from hypothesis.searchstrategy.wrappers import WrapperStrategy
from hypothesis.searchstrategy.strategies import OneOfStrategy, \
    SearchStrategy


class LimitReached(BaseException):
    pass


class LimitedStrategy(WrapperStrategy):

    def __init__(self, strategy):
        super(LimitedStrategy, self).__init__(strategy)
        self.marker = 0
        self.currently_capped = False

    def do_draw(self, data):
        assert self.currently_capped
        if self.marker <= 0:
            raise LimitReached()
        self.marker -= 1
        return super(LimitedStrategy, self).do_draw(data)

    @contextmanager
    def capped(self, max_templates):
        assert not self.currently_capped
        try:
            self.currently_capped = True
            self.marker = max_templates
            yield
        finally:
            self.currently_capped = False


class RecursiveStrategy(SearchStrategy):

    def __init__(self, base, extend, max_leaves):
        self.max_leaves = max_leaves
        self.base = LimitedStrategy(base)
        self.extend = extend

        strategies = [self.base, self.extend(self.base)]
        while 2 ** len(strategies) <= max_leaves:
            strategies.append(
                extend(OneOfStrategy(tuple(strategies), bias=0.8)))
        self.strategy = OneOfStrategy(strategies)

    def validate(self):
        self.base.validate()
        self.extend(self.base).validate()

    def do_draw(self, data):
        while True:
            try:
                with self.base.capped(self.max_leaves):
                    return data.draw(self.strategy)
            except LimitReached:
                pass
