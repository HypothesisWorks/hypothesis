# coding=utf-8

# Copyright (C) 2013-2015 David R. MacIver (david@drmaciver.com)

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

from __future__ import division, print_function, absolute_import, \
    unicode_literals

from random import Random
from collections import namedtuple

from hypothesis.descriptors import one_of, \
    sampled_from
from hypothesis.searchstrategy import RandomWithSeed, SearchStrategy, MappedSearchStrategy, \
    nice_string
from hypothesis.internal.compat import text_type, binary_type
from hypothesis.searchstrategy.narytree import NAryTree, Leaf
from hypothesis.strategytable import StrategyTable

primitive_types = [
    int, float, text_type, binary_type, bool, complex, type(None)]


Descriptor = namedtuple('Descriptor', ('descriptor',))


class DescriptorWithValue(object):

    def __init__(self, descriptor, template, value, random):
        self.descriptor = descriptor
        self.value = value
        self.template = template
        self.random = random

    def __iter__(self):
        yield self.descriptor
        yield self.value
        yield self.template
        yield self.random

    def __len__(self):
        return 4

    def __repr__(self):
        return (
            'DescriptorWithValue(descriptor=%s, template=%r, '
            'value=%r, random=%r)'
        ) % (
            nice_string(self.descriptor), self.template, self.value,
            self.random,
        )


class DescriptorStrategy(MappedSearchStrategy):

    def __init__(self):
        super(DescriptorStrategy, self).__init__(
            descriptor=Descriptor,
            strategy=StrategyTable.default().strategy(NAryTree(
                branch_labels=sampled_from((
                    tuple, dict, set, frozenset, list
                )),
                branch_keys=one_of((int, str)),
                leaf_values=sampled_from((
                    int, float, text_type, binary_type,
                    bool, complex, type(None)))
            ))
        )

    def pack(self, value):
        if isinstance(value, Leaf):
            return value.value
        else:
            label = value.label
            if label == dict:
                return {
                    k: self.pack(v)
                    for k, v in value.keyed_children
                }
            else:
                children = [self.pack(v) for k, v in value.keyed_children]
                try:
                    return label(children)
                except TypeError:
                    return tuple(children)

StrategyTable.default().define_specification_for(
    Descriptor, lambda s, d: DescriptorStrategy())


class DescriptorWithValueStrategy(SearchStrategy):
    descriptor = DescriptorWithValue

    def __init__(self, strategy_table):
        descriptor_strategy = strategy_table.strategy(Descriptor)
        self.descriptor_strategy = descriptor_strategy
        self.parameter = descriptor_strategy.parameter
        self.strategy_table = strategy_table
        self.random_strategy = strategy_table.strategy(Random)

    def produce_template(self, random, pv):
        descriptor_template = self.descriptor_strategy.produce_template(
            random, pv)
        descriptor = self.descriptor_strategy.reify(descriptor_template)
        strategy = self.strategy_table.strategy(descriptor)
        parameter = strategy.parameter.draw(random)
        template = strategy.produce_template(random, parameter)
        new_random = self.random_strategy.draw_and_produce(random)
        return DescriptorWithValue(
            descriptor=descriptor_template,
            template=template,
            value=None,
            random=new_random
        )

    def reify(self, davt):
        descriptor = self.descriptor_strategy.reify(davt.descriptor)
        return DescriptorWithValue(
            descriptor=descriptor,
            template=davt.template,
            value=self.strategy_table.strategy(descriptor).reify(
                davt.template),
            random=RandomWithSeed(davt.random),
        )

    def simplify(self, davt):
        random = RandomWithSeed(davt.random)
        for d in self.descriptor_strategy.simplify(davt.descriptor):
            new_template = self.strategy_table.strategy(
                self.descriptor_strategy.reify(d)).draw_and_produce(random)
            yield DescriptorWithValue(
                descriptor=d,
                template=new_template,
                value=None,
                random=davt.random,
            )

        strategy = self.strategy_table.strategy(
            self.descriptor_strategy.reify(davt.descriptor))

        for v in strategy.simplify(davt.template):
            yield DescriptorWithValue(
                descriptor=davt.descriptor,
                template=v,
                value=None,
                random=davt.random,
            )


StrategyTable.default().define_specification_for(
    DescriptorWithValue,
    lambda s, d: DescriptorWithValueStrategy(s),
)
