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

from copy import deepcopy
from random import Random

from hypothesis.utils.idkey import IdKey
from hypothesis.internal.compat import OrderedDict, hrange, integer_types
from hypothesis.searchstrategy.strategies import BadData, SearchStrategy, \
    check_length, check_data_type


class Morpher(object):

    def __init__(self, parameter_seed, template_seed, data=None):
        self.parameter_seed = parameter_seed
        self.template_seed = template_seed
        self.cache = OrderedDict()
        self.data = list(data or ())
        self.owners = []
        self.generation = 0
        self.old_cache = None

    def __eq__(self, other):
        return isinstance(other, Morpher) and (
            self.parameter_seed == other.parameter_seed and
            self.template_seed == other.template_seed and
            self.data == other.data
        )

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(self.parameter_seed) ^ hash(self.template_seed)

    def __copy__(self):
        result = self.clean_slate()
        result.old_cache = deepcopy(self.old_cache)
        result.cache = deepcopy(self.cache)
        return result

    def clean_slate(self):
        result = Morpher(self.parameter_seed, self.template_seed, self.data)
        for s in self.strategies():
            template = result.template_for(s)
            basic = s.to_basic(template)
            result.data[result.owners.index(s)] = basic
        result.cache = {}
        result.owners = []
        return result

    def __deepcopy__(self, table):
        return self.__copy__()

    def owner(self, i):
        if i >= len(self.owners):
            return None
        return self.owners[i]

    def set_owner(self, i, owner):
        while i >= len(self.owners):
            self.owners.append(None)
        self.owners[i] = owner

    def template_for(self, strategy):
        key = IdKey(strategy)
        try:
            return self.cache[key]
        except KeyError:
            pass
        for i, data in enumerate(self.data):
            try:
                existing = self.owner(i)
                assert existing is not strategy
                if existing is None:
                    template = strategy.from_basic(data)
                    self.set_owner(i, strategy)
                    break
            except BadData:
                pass
        else:
            parameter = strategy.draw_parameter(
                Random(self.parameter_seed))
            template = strategy.draw_template(
                Random(self.template_seed), parameter)
            basic = strategy.to_basic(template)
            self.data.append(basic)
            template = strategy.from_basic(basic)
            self.set_owner(len(self.data) - 1, strategy)
        self.cache[key] = template
        return template

    def become(self, strategy):
        return strategy.reify(self.template_for(strategy))

    def __trackas__(self):
        return [
            self.parameter_seed, self.template_seed, len(self.cache),
            self.data,
        ]

    def __repr__(self):
        return 'Morpher(%s)' % (', '.join([
            ('%r -> %r') % (key.value, template)
            for (key, template) in self.cache.items()
        ] + list(map(repr, self.data))),)

    def replace_template(self, strategy, template):
        result = Morpher(
            self.parameter_seed, self.template_seed, self.data)
        for s in self.strategies():
            result.template_for(s)
        result.template_for(strategy)
        i = result.owners.index(strategy)
        assert result.owners[i] is strategy
        result.data[i] = strategy.to_basic(template)
        return result

    def without_deadweight(self):
        result = Morpher(
            self.parameter_seed, self.template_seed, [
                self.data[i]
                for i in hrange(len(self.data)) if self.owner(i) is not None])
        for s in self.strategies():
            result.template_for(s)
        return result

    def collapse(self):
        self.restore()
        self.old_cache = self.cache
        self.cache = OrderedDict()
        self.owners = []

    def strategies(self):
        if self.cache:
            return [k.value for k in self.cache]
        elif self.old_cache:
            return [k.value for k in self.old_cache]
        else:
            return []

    def restore(self):
        if not self.cache and self.old_cache is not None:
            self.owners = []
            for key in self.old_cache:
                self.template_for(key.value)
        self.old_cache = None


class MorpherStrategy(SearchStrategy):

    def draw_parameter(self, random):
        return random.getrandbits(64)

    def strictly_simpler(self, x, y):
        if x == y:
            return False
        xstrat = x.strategies()
        ystrat = y.strategies()
        if not (xstrat or ystrat):
            return x.template_seed < y.template_seed
        if xstrat and not ystrat:
            return True
        if ystrat and not xstrat:
            return False

        def direction_for(strats):
            u = x.clean_slate()
            v = y.clean_slate()
            for s in strats:
                us = u.template_for(s)
                vs = v.template_for(s)
                if s.strictly_simpler(us, vs):
                    return -1
                if s.strictly_simpler(vs, us):
                    return 1
            return 0

        by_x = direction_for(xstrat)
        by_y = direction_for(ystrat)
        return max(by_x, by_y) <= 0 and min(by_x, by_y) < 0

    def draw_template(self, random, parameter):
        return Morpher(
            parameter_seed=parameter,
            template_seed=random.getrandbits(64),
        )

    def reify(self, template):
        template.collapse()
        return template

    def simplifiers(self, random, morpher):
        morpher.restore()
        for key, template in morpher.cache.items():
            strategy = key.value
            for simplifier in strategy.simplifiers(random, template):
                yield self.convert_simplifier(strategy, simplifier)

    def convert_simplifier(self, strategy, simplifier):
        def accept(random, morpher):
            morpher = morpher.clean_slate()
            template = morpher.template_for(strategy)
            for new_template in simplifier(random, template):
                yield morpher.replace_template(
                    strategy, new_template
                ).clean_slate()
        accept.__name__ = str(
            'convert_simplifier(..., %s)' % (simplifier.__name__,)
        )
        return accept

    def from_basic(self, data):
        check_length(3, data)
        check_data_type(integer_types, data[0])
        check_data_type(integer_types, data[1])
        check_data_type(list, data[2])
        return Morpher(
            parameter_seed=data[0], template_seed=data[1], data=data[2])

    def to_basic(self, template):
        template = template.clean_slate()
        return [template.parameter_seed, template.template_seed, template.data]
