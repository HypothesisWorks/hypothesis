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

from __future__ import division, print_function, absolute_import

import inspect

from hypothesis.searchstrategy.wrappers import WrapperStrategy


class ReprWrapperStrategy(WrapperStrategy):

    """A strategy which is defined purely by conversion to and from another
    strategy.

    Its parameter and distribution come from that other strategy.

    """

    def __init__(self, strategy, representation):
        super(ReprWrapperStrategy, self).__init__(strategy)
        self.representation = representation

    def __repr__(self):
        if inspect.isfunction(self.representation):
            self.representation = self.representation()
        return self.representation

    def draw_parameter(self, random):
        return self.wrapped_strategy.draw_parameter(random)

    def draw_template(self, random, pv):
        return self.wrapped_strategy.draw_template(random, pv)

    def reify(self, value):
        return self.wrapped_strategy.reify(value)

    def simplifiers(self, random, template):
        return self.wrapped_strategy.simplifiers(random, template)

    def strictly_simpler(self, x, y):
        return self.wrapped_strategy.strictly_simpler(x, y)

    def to_basic(self, template):
        return self.wrapped_strategy.to_basic(template)

    def from_basic(self, data):
        return self.wrapped_strategy.from_basic(data)
