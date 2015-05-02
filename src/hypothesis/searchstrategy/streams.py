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

from hypothesis.types import Stream
from hypothesis.specifiers import Streaming
from hypothesis.utils.show import show
from hypothesis.internal.compat import hrange, integer_types
from hypothesis.searchstrategy.strategies import BuildContext, \
    SearchStrategy, strategy, check_length, check_data_type


class StreamTemplate(object):

    def __init__(self, seed, parameter, generator, changed=0):
        self.seed = seed
        self.parameter_seed = parameter
        self.changed = changed
        if isinstance(generator, Stream):
            self.stream = generator
        else:
            self.stream = Stream(generator)

    def __repr__(self):
        return 'StreamTemplate(%r, %r, (%s))' % (
            self.seed, self.parameter_seed,
            ', '.join(map(show, self.stream[:self.changed]))
        )

    def __eq__(self, other):
        if not isinstance(other, StreamTemplate):
            return False
        if self.seed != other.seed:
            return False
        if self.parameter_seed != other.parameter_seed:
            return False
        common_max = max(self.changed, other.changed)
        return (
            list(self.stream[:common_max]) ==
            list(other.stream[:common_max])
        )

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(self.seed ^ self.parameter_seed)

    def with_value(self, i, value):
        return StreamTemplate(
            self.seed, self.parameter_seed,
            self.stream.with_value(i, value),
            max(i + 1, self.changed)
        )

    def __trackas__(self):
        return ('StreamTemplate', self.seed, list(self.stream[:self.changed]))


class StreamStrategy(SearchStrategy):

    def __init__(self, source_strategy):
        super(StreamStrategy, self).__init__()
        self.source_strategy = source_strategy

    def __repr__(self):
        return 'StreamStrategy(%r)' % (self.source_strategy,)

    def produce_parameter(self, random):
        return random.getrandbits(64)

    def produce_template(self, context, parameter):
        return self.new_template(context.random.getrandbits(64), parameter)

    def new_template(self, seed, parameter_seed):
        context = BuildContext(Random(seed))
        parameter = self.source_strategy.draw_parameter(Random(parameter_seed))

        def templates():
            while True:
                yield self.source_strategy.draw_template(context, parameter)
        return StreamTemplate(seed, parameter_seed, templates())

    def simplifiers(self, random, template):
        for i in hrange(len(template.stream.fetched)):
            for s in self.source_strategy.simplifiers(
                random, template.stream[i]
            ):
                yield self.simplifier_for_index(s, i)

    def strictly_simpler(self, x, y):
        for i in hrange(max(x.changed, y.changed)):
            u = x.stream[i]
            v = y.stream[i]
            if self.source_strategy.strictly_simpler(u, v):
                return True
            if self.source_strategy.strictly_simpler(v, u):
                return False
        return x.seed < y.seed

    def simplifier_for_index(self, simplify, i):
        def accept(random, template):
            stream = template.stream
            stream._thunk_to(i + 1)
            for t in simplify(random, stream[i]):
                yield template.with_value(i, t)
        accept.__name__ = str(
            'simplifier_for_index(%s, %d)' % (
                simplify.__name__, i
            )
        )
        return accept

    def reify(self, template):
        return template.stream.map(self.source_strategy.reify)

    def to_basic(self, template):
        assert isinstance(template.parameter_seed, integer_types)
        return [
            template.seed,
            template.parameter_seed,
            list(map(
                self.source_strategy.to_basic,
                template.stream[:template.changed]))
        ]

    def from_basic(self, data):
        check_data_type(list, data)
        check_length(3, data)
        check_data_type(integer_types, data[0])
        check_data_type(integer_types, data[1])
        template = self.new_template(data[0], data[1])
        check_data_type(list, data[2])
        changed = list(map(self.source_strategy.from_basic, data[2]))
        template.stream._thunk_to(len(changed))
        assert len(template.stream.fetched) == len(changed)
        template.changed = len(changed)
        template.stream.fetched = changed
        return template


@strategy.extend(Streaming)
def stream_strategy(streaming, settings):
    return StreamStrategy(strategy(streaming.data, settings))
