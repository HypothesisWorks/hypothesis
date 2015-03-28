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
from hypothesis.specifiers import one_of, sampled_from
from hypothesis.utils.show import show
from hypothesis.internal.compat import text_type, binary_type
from hypothesis.searchstrategy.narytree import Leaf, NAryTree
from hypothesis.searchstrategy.strategies import BuildContext, \
    SearchStrategy, MappedSearchStrategy, strategy, check_length, \
    check_data_type

primitive_types = [
    int, float, text_type, binary_type, bool, complex, type(None)]


Descriptor = namedtuple('Descriptor', ('specifier',))


class DescriptorWithValue(object):

    def __init__(self, specifier, template, value, random):
        self.specifier = specifier
        self.value = value
        self.template = template
        self.random = random

    def __iter__(self):
        yield self.specifier
        yield self.value
        yield self.template
        yield self.random

    def __len__(self):
        return 4

    def __repr__(self):
        return (
            'DescriptorWithValue(specifier=%s, template=%r, '
            'value=%r, random=%r)'
        ) % (
            show(self.specifier), self.template, self.value,
            self.random,
        )


class DescriptorStrategy(MappedSearchStrategy):

    def __init__(self, settings):
        super(DescriptorStrategy, self).__init__(
            strategy=strategy(NAryTree(
                branch_labels=sampled_from((
                    tuple, dict, set, frozenset, list
                )),
                branch_keys=one_of((int, str)),
                leaf_values=sampled_from((
                    int, float, text_type, binary_type,
                    bool, complex, type(None)))
            ), settings)
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
def specifier_strategy(cls, settings):
    return DescriptorStrategy(settings)


class DescriptorWithValueStrategy(SearchStrategy):
    specifier = DescriptorWithValue

    def __init__(self, settings):
        self.settings = settings
        specifier_strategy = strategy(Descriptor, settings)
        self.specifier_strategy = specifier_strategy
        self.random_strategy = strategy(Random, settings)

    def strategy(self, specifier):
        return strategy(specifier, self.settings)

    def produce_parameter(self, random):
        return self.specifier_strategy.draw_parameter(random)

    def produce_template(self, context, pv):
        specifier_template = self.specifier_strategy.draw_template(
            context, pv)
        specifier = self.specifier_strategy.reify(specifier_template)
        strat = self.strategy(specifier)
        parameter = strat.draw_parameter(context.random)
        template = strat.draw_template(context, parameter)
        new_random = self.random_strategy.draw_and_produce(context)
        return DescriptorWithValue(
            specifier=specifier_template,
            template=template,
            value=None,
            random=new_random
        )

    def reify(self, davt):
        specifier = self.specifier_strategy.reify(davt.specifier)
        return DescriptorWithValue(
            specifier=specifier,
            template=davt.template,
            value=self.strategy(specifier).reify(
                davt.template),
            random=RandomWithSeed(davt.random),
        )

    def basic_simplify(self, davt):
        random = RandomWithSeed(davt.random)
        for d in self.specifier_strategy.full_simplify(davt.specifier):
            new_template = self.strategy(
                self.specifier_strategy.reify(d)).draw_and_produce(
                    BuildContext(random))
            yield DescriptorWithValue(
                specifier=d,
                template=new_template,
                value=None,
                random=davt.random,
            )

        strat = self.strategy(
            self.specifier_strategy.reify(davt.specifier))

        for v in strat.full_simplify(davt.template):
            yield DescriptorWithValue(
                specifier=davt.specifier,
                template=v,
                value=None,
                random=davt.random,
            )

    def to_basic(self, value):
        strat = self.strategy(
            self.specifier_strategy.reify(value.specifier))
        return [
            self.specifier_strategy.to_basic(value.specifier),
            value.random,
            strat.to_basic(value.template)
        ]

    def from_basic(self, data):
        check_data_type(list, data)
        check_length(3, data)
        specifier, random, template = data
        dt = self.specifier_strategy.from_basic(specifier)
        d = self.specifier_strategy.reify(dt)
        vt = self.strategy(d).from_basic(template)
        return DescriptorWithValue(
            random=random, specifier=dt, template=vt, value=None
        )


@strategy.extend_static(DescriptorWithValue)
def dav_strategy(cls, settings):
    return DescriptorWithValueStrategy(settings)
