# coding=utf-8

# Copyright (C) 2013-2015 David R. MacIver (david@drmaciver.com)

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

from __future__ import division, print_function, absolute_import, \
    unicode_literals

import hypothesis.descriptors as descriptors
from hypothesis.internal.specmapper import SpecificationMapper

from . import strategy as strat


def convert_strategy(fn):
    if isinstance(fn, strat.SearchStrategy):
        return lambda strategies, descriptor: fn
    return fn


def strategy_for(typ):
    def accept_function(fn):
        StrategyTable.default().define_specification_for(
            typ, convert_strategy(fn))
        return fn
    return accept_function


def strategy_for_instances(typ):
    def accept_function(fn):
        StrategyTable.default().define_specification_for_instances(
            typ, convert_strategy(fn))
        return fn
    return accept_function


class StrategyTable(SpecificationMapper):

    def __init__(self, prototype=None, examples_for=None):
        super(StrategyTable, self).__init__(prototype=prototype)
        self.examples_for = examples_for or (lambda d: ())

    def _calculate_specification_for(self, descriptor):
        base_specification = super(
            StrategyTable, self)._calculate_specification_for(descriptor)
        examples = self.examples_for(descriptor)
        if not examples:
            return base_specification
        else:
            return strat.ExampleAugmentedStrategy(
                main_strategy=base_specification,
                examples=examples,
            )

    def augment_with_examples(self, examples_for):
        c = self.new_child_mapper()
        c.examples_for = examples_for
        return c

    def strategy(self, descriptor):
        return self.specification_for(descriptor)


@strategy_for_instances(descriptors.OneOf)
def define_one_of_strategy(strategies, descriptor):
    return strat.OneOfStrategy(map(strategies.strategy, descriptor.elements))
