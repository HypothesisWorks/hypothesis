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

from collections import namedtuple

from hypothesis import Settings
from hypothesis.strategies import lists, tuples
from hypothesis.internal.compat import hrange
from hypothesis.internal.distributions import geometric, uniform_float
from hypothesis.searchstrategy.strategies import BadData, strategy, \
    check_length, SearchStrategy, check_data_type

NAryTree = namedtuple(u'NAryTree', (
    u'branch_labels',
    u'leaf_values',
    u'branch_keys',
))

Leaf = namedtuple(u'Leaf', (
    u'value',
))

Branch = namedtuple(u'Branch', (
    u'label',
    u'keyed_children',
))


class NAryTreeStrategy(SearchStrategy):
    Parameter = namedtuple(
        u'Parameter', (
            u'leaf_parameter', u'branch_key_parameter',
            u'branch_label_parameter', u'branch_factor'
        )
    )

    def __init__(self, specifier, settings):
        self.specifier = specifier
        self.leaf_strategy = strategy(specifier.leaf_values, settings)
        self.branch_key_strategy = strategy(
            specifier.branch_keys, settings)
        self.branch_label_strategy = strategy(
            specifier.branch_labels, settings)

        self.child_strategy = (
            lists(tuples(self.branch_key_strategy, self)))

    def __repr__(self):
        return u'NAryTreeStrategy(leaves=%r, labels=%r, keys=%r)' % (
            self.leaf_strategy, self.branch_label_strategy,
            self.branch_key_strategy
        )

    def draw_parameter(self, random):
        return self.Parameter(
            leaf_parameter=self.leaf_strategy.draw_parameter(random),
            branch_key_parameter=self.branch_key_strategy.draw_parameter(
                random),
            branch_label_parameter=self.branch_label_strategy.draw_parameter(
                random),
            branch_factor=uniform_float(random, 0.75, 0.99),
        )

    def draw_template(self, random, pv):
        n_children = geometric(random, pv.branch_factor)
        if not n_children:
            return Leaf(self.leaf_strategy.draw_template(
                random, pv.leaf_parameter
            ))
        else:
            children = tuple(
                (self.branch_key_strategy.draw_template(
                    random, pv.branch_key_parameter),
                 self.draw_template(random, pv))
                for _ in hrange(n_children))
            label = self.branch_label_strategy.draw_template(
                random, pv.branch_label_parameter
            )
            return Branch(
                label=label, keyed_children=children
            )

    def reify(self, template):
        if isinstance(template, Leaf):
            return Leaf(
                self.leaf_strategy.reify(template.value)
            )
        else:
            assert isinstance(template, Branch)
            return Branch(
                label=self.branch_label_strategy.reify(template.label),
                keyed_children=tuple(
                    (
                        self.branch_key_strategy.reify(k),
                        self.reify(v))
                    for k, v in template.keyed_children
                ))

    def basic_simplify(self, random, template):
        if isinstance(template, Branch):
            for k, v in template.keyed_children:
                yield v
            for l in (
                self.branch_label_strategy.full_simplify(
                    random, template.label)):
                yield Branch(l, template.keyed_children)
            for cs in self.child_strategy.full_simplify(
                random,
                template.keyed_children
            ):
                yield Branch(template.label, cs)
        else:
            for v in self.leaf_strategy.full_simplify(random, template.value):
                yield Leaf(v)

    def to_basic(self, template):
        if isinstance(template, Leaf):
            return [self.leaf_strategy.to_basic(template.value)]
        else:
            assert isinstance(template, Branch)
            return [
                self.branch_label_strategy.to_basic(template.label), [
                    [self.branch_key_strategy.to_basic(k),
                     self.to_basic(v)]
                    for k, v in template.keyed_children]
            ]

    def from_basic(self, data):
        check_data_type(list, data)
        if not (1 <= len(data) <= 2):
            raise BadData(
                u'Expected list of length 1 or 2 but got %r' % (data,))

        if len(data) == 1:
            return Leaf(self.leaf_strategy.from_basic(data[0]))
        else:
            check_length(2, data)
            check_data_type(list, data[1])
            for v in data[1]:
                check_length(2, v)
            return Branch(
                label=self.branch_label_strategy.from_basic(data[0]),
                keyed_children=tuple(
                    (self.branch_key_strategy.from_basic(k),
                     self.from_basic(v))
                    for k, v in data[1]))


@strategy.extend(NAryTree)
def nary_tree_strategy(specifier, settings):
    return NAryTreeStrategy(specifier, settings)


def n_ary_tree(*args, **kwargs):
    return NAryTreeStrategy(NAryTree(*args, **kwargs), Settings.default)
