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

import hypothesis.params as params
from tests.common import small_table
from hypothesis.descriptors import Just, OneOf, SampledFrom, just, \
    sampled_from
from hypothesis.searchstrategy import RandomWithSeed, SearchStrategy, \
    nice_string
from hypothesis.internal.compat import hrange, text_type, binary_type
from hypothesis.database.converter import ConverterTable
from hypothesis.internal.utils.distributions import geometric, biased_coin

primitive_types = [int, float, text_type, binary_type, bool, complex]
basic_types = list(primitive_types)
basic_types.append(OneOf(tuple(basic_types)))
basic_types += [frozenset({x}) for x in basic_types]
basic_types += [set({x}) for x in basic_types]
basic_types.append(Random)
branch_types = [dict, tuple, list]

Descriptor = namedtuple('Descriptor', ('descriptor',))


class DescriptorWithValue(object):

    def __init__(self, descriptor, value, random):
        self.descriptor = descriptor
        self.value = value
        self.random = random
        assert small_table.strategy(self.descriptor).could_have_produced(
            self.value
        )

    def __iter__(self):
        yield self.descriptor
        yield self.value
        yield self.random

    def __len__(self):
        return 3

    def __repr__(self):
        return 'DescriptorWithValue(descriptor=%s, value=%r, random=%r)' % (
            nice_string(self.descriptor), self.value, self.random,
        )

ConverterTable.default().mark_not_serializeable(Descriptor)
ConverterTable.default().mark_not_serializeable(DescriptorWithValue)


class DescriptorStrategy(SearchStrategy):
    descriptor = Descriptor

    def __init__(self):
        self.key_strategy = small_table.strategy(
            OneOf((text_type, binary_type, int, bool))
        )
        self.sampling_strategy = small_table.strategy(primitive_types)
        self.parameter = params.CompositeParameter(
            leaf_descriptors=params.NonEmptySubset(basic_types),
            branch_descriptors=params.NonEmptySubset(branch_types),
            branch_factor=params.UniformFloatParameter(0.6, 0.99),
            key_parameter=self.key_strategy.parameter,
            just_probability=params.UniformFloatParameter(0, 0.45),
            sampling_probability=params.UniformFloatParameter(0, 0.45),
            sampling_param=self.sampling_strategy.parameter,
        )

    def produce(self, random, pv):
        n_children = geometric(random, pv.branch_factor)
        if not n_children:
            return random.choice(pv.leaf_descriptors)
        elif n_children == 1 and biased_coin(random, pv.just_probability):
            new_desc = self.produce(random, pv)
            child_strategy = small_table.strategy(new_desc)
            pv2 = child_strategy.parameter.draw(random)
            return just(child_strategy.produce(random, pv2))
        elif n_children == 1 and biased_coin(random, pv.sampling_probability):
            elements = self.sampling_strategy.produce(
                random, pv.sampling_param)
            if elements:
                return sampled_from(elements)

        children = [self.produce(random, pv) for _ in hrange(n_children)]
        combiner = random.choice(pv.branch_descriptors)
        if combiner != dict:
            return combiner(children)
        else:
            result = {}
            for v in children:
                k = self.key_strategy.produce(random, pv.key_parameter)
                result[k] = v
            return result

    def simplify(self, value):
        if isinstance(value, dict):
            children = list(value.values())
        elif isinstance(value, (Just, SampledFrom)):
            return
        elif isinstance(value, (list, set, tuple)):
            children = list(value)
        else:
            return
        for child in children:
            yield child

    def could_have_produced(self, value):
        return True


small_table.define_specification_for(
    Descriptor, lambda s, d: DescriptorStrategy())


class DescriptorWithValueStrategy(SearchStrategy):
    descriptor = DescriptorWithValue

    def __init__(self, strategy_table):
        descriptor_strategy = strategy_table.strategy(Descriptor)
        self.descriptor_strategy = descriptor_strategy
        self.parameter = descriptor_strategy.parameter
        self.strategy_table = strategy_table
        self.random_strategy = strategy_table.strategy(Random)

    def produce(self, random, pv):
        descriptor = self.descriptor_strategy.produce(random, pv)
        strategy = self.strategy_table.strategy(descriptor)
        parameter = strategy.parameter.draw(random)
        value = strategy.produce(random, parameter)
        new_random = self.random_strategy.draw_and_produce(random)
        assert strategy.could_have_produced(value)
        return DescriptorWithValue(
            descriptor=descriptor,
            value=value,
            random=new_random,
        )

    def simplify(self, dav):
        strat = self.strategy_table.strategy(dav.descriptor)
        for d, v in strat.decompose(dav.value):
            stratd = self.strategy_table.strategy(d)
            assert stratd.could_have_produced(v)
            yield DescriptorWithValue(
                descriptor=d,
                value=v,
                random=RandomWithSeed(dav.random.seed)
            )


small_table.define_specification_for(
    DescriptorWithValue,
    lambda s, d: DescriptorWithValueStrategy(s),
)
