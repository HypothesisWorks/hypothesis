# coding=utf-8

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# Most of this work is copyright (C) 2013-2015 David R. MacIver
# (david@drmaciver.com), but it contains contributions by other. See
# https://github.com/DRMacIver/hypothesis/blob/master/CONTRIBUTING.rst for a
# full list of people who may hold copyright, and consult the git log if you
# need to determine who owns an individual contribution.

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

from __future__ import division, print_function, absolute_import, \
    unicode_literals

from hypothesis.internal.compat import hrange
from hypothesis.searchstrategy.wrappers import WrapperStrategy
from hypothesis.searchstrategy.strategies import OneOfStrategy


class TemplateLimitReached(BaseException):
    pass


class TemplateLimitedStrategy(WrapperStrategy):

    def __init__(self, strategy):
        super(TemplateLimitedStrategy, self).__init__(strategy)
        self.marker = 0

    def draw_template(self, random, parameter_value):
        if self.marker <= 0:
            raise TemplateLimitReached()
        self.marker -= 1
        return super(TemplateLimitedStrategy, self).draw_template(
            random, parameter_value)

    def set_max_templates(self, max_templates):
        self.marker = max_templates


class LimitAwareOneOf(OneOfStrategy):

    def __init__(self, strategies, base, limit):
        super(LimitAwareOneOf, self).__init__(strategies)
        self.base = base
        self.limit = limit

    def redraw_simplifier(self, child):
        def accept(random, template):
            i, value = template
            if child >= i:
                return
            for _ in hrange(20):
                self.base.set_max_templates(self.limit)
                try:
                    redraw = self.element_strategies[child].draw_and_produce(
                        random)
                    yield child, redraw
                # This is reachable by tests but is incredibly hard to hit
                # reliably.
                except TemplateLimitReached:  # pragma: no cover
                    continue
        accept.__name__ = str(
            'redraw_simplifier(%d)' % (child,))
        return accept


class RecursiveStrategy(WrapperStrategy):

    def __init__(self, base, extend, max_leaves):
        self.max_leaves = max_leaves
        self.base = TemplateLimitedStrategy(base)
        self.extend = extend

        strategies = [self.base, self.extend(self.base)]
        while 2 ** len(strategies) <= max_leaves:
            strategies.append(
                extend(LimitAwareOneOf(
                    tuple(strategies), self.base, self.max_leaves)))
        super(RecursiveStrategy, self).__init__(
            LimitAwareOneOf(strategies, self.base, self.max_leaves)
        )

    def draw_parameter(self, random):
        while True:
            pv = super(RecursiveStrategy, self).draw_parameter(random)
            try:
                self.base.set_max_templates(self.max_leaves)
                super(
                    RecursiveStrategy, self).draw_template(random, pv)
                return pv
            except TemplateLimitReached:
                pass

    def draw_template(self, random, pv):
        while True:
            try:
                self.base.set_max_templates(self.max_leaves)
                return super(RecursiveStrategy, self).draw_template(
                    random, pv
                )
            except TemplateLimitReached:
                pass
