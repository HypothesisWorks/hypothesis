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

from hypothesis.types import RandomWithSeed
from hypothesis.descriptors import one_of, sampled_from
from hypothesis.searchstrategy import SearchStrategy, \
    MappedSearchStrategy, check_length, check_data_type, strategy
from hypothesis.internal.compat import text_type, binary_type
from hypothesis.internal.fixers import nice_string
from hypothesis.searchstrategy.narytree import Leaf, NAryTree

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
            strategy=strategy(NAryTree(
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


@strategy.extend_static(Descriptor)
def descriptor_strategy(cls):
    return DescriptorStrategy()


class DescriptorWithValueStrategy(SearchStrategy):
    descriptor = DescriptorWithValue

    def __init__(self):
        descriptor_strategy = strategy(Descriptor)
        self.descriptor_strategy = descriptor_strategy
        self.parameter = descriptor_strategy.parameter
        self.random_strategy = strategy(Random)

    def produce_template(self, random, pv):
        descriptor_template = self.descriptor_strategy.produce_template(
            random, pv)
        descriptor = self.descriptor_strategy.reify(descriptor_template)
        strat = strategy(descriptor)
        parameter = strat.parameter.draw(random)
        template = strat.produce_template(random, parameter)
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
            value=strategy(descriptor).reify(
                davt.template),
            random=RandomWithSeed(davt.random),
        )

    def simplify(self, davt):
        random = RandomWithSeed(davt.random)
        for d in self.descriptor_strategy.simplify(davt.descriptor):
            new_template = strategy(
                self.descriptor_strategy.reify(d)).draw_and_produce(random)
            yield DescriptorWithValue(
                descriptor=d,
                template=new_template,
                value=None,
                random=davt.random,
            )

        strat = strategy(
            self.descriptor_strategy.reify(davt.descriptor))

        for v in strat.simplify(davt.template):
            yield DescriptorWithValue(
                descriptor=davt.descriptor,
                template=v,
                value=None,
                random=davt.random,
            )

    def to_basic(self, value):
        strat = strategy(
            self.descriptor_strategy.reify(value.descriptor))
        return [
            self.descriptor_strategy.to_basic(value.descriptor),
            value.random,
            strat.to_basic(value.template)
        ]

    def from_basic(self, data):
        check_data_type(list, data)
        check_length(3, data)
        descriptor, random, template = data
        dt = self.descriptor_strategy.from_basic(descriptor)
        d = self.descriptor_strategy.reify(dt)
        vt = strategy(d).from_basic(template)
        return DescriptorWithValue(
            random=random, descriptor=dt, template=vt, value=None
        )


@strategy.extend_static(DescriptorWithValue)
def dav_strategy(cls):
    return DescriptorWithValueStrategy()
