# coding=utf-8

# Copyright (C) 2013-2015 David R. MacIver (david@drmaciver.com)

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

from __future__ import division, print_function, unicode_literals

from random import Random

from hypothesis.internal.compat import hrange


class ExampleSource(object):

    """An object that provides you with an a stream of examples to work with.

    Starts by fetching examples from storage if storage has been provided but
    if storage is None will happily continue without. Follows by generating new
    examples, but if the strategy is None then will stop there. Must have at
    least one of strategy and storage but does not have to have both.

    This does not handle deduplication or make decisions as to when to stop.
    That's up to the caller.

    """

    def __init__(
        self,
        random, strategy, storage,
        min_parameters=25, min_tries=2,
    ):
        if not isinstance(random, Random):
            raise ValueError('A Random is required but got %r' % (random,))
        if strategy is None and storage is None:
            raise ValueError(
                'Cannot proceed without at least one way of getting examples'
            )
        self.strategy = strategy
        self.storage = storage
        self.random = random
        self.parameters = []
        self.last_parameter_index = -1
        self.min_parameters = min_parameters
        self.min_tries = min_tries
        self.bad_counts = []
        self.counts = []
        self.total_count = 0
        self.total_bad_count = 0
        self.mark_set = False
        self.started = False

    def mark_bad(self):
        """The last example was bad.

        If possible can we have less of that please?

        """
        if not self.started:
            raise ValueError('No examples have been generated yet')
        if self.mark_set:
            raise ValueError('This parameter has already been marked')
        self.mark_set = True
        if self.last_parameter_index < 0:
            return
        self.total_bad_count += 1
        self.bad_counts[self.last_parameter_index] += 1

    def new_parameter(self):
        result = self.strategy.parameter.draw(self.random)
        self.parameters.append(result)
        self.bad_counts.append(0)
        self.counts.append(1)
        return result

    def draw_parameter_score(self, i):
        beta_prior = 2.0 * (
            1.0 + self.total_bad_count
        ) / (1.0 + self.total_count)
        alpha_prior = 2.0 - beta_prior

        beta = beta_prior + self.bad_counts[i]
        alpha = alpha_prior + self.counts[i] - self.bad_counts[i]
        assert self.counts[i] > 0
        assert self.bad_counts[i] >= 0
        assert self.bad_counts[i] <= self.counts[i]
        return self.random.betavariate(alpha, beta)

    def pick_a_parameter(self):
        self.mark_set = False
        self.total_count += 1
        if self.parameters and self.counts[-1] < self.min_tries:
            index = len(self.parameters) - 1
            self.counts[index] += 1
            self.last_parameter_index = index
            return self.parameters[index]
        if len(self.parameters) < self.min_parameters:
            return self.new_parameter()
        else:
            best_score = self.draw_parameter_score(
                self.random.randint(0, len(self.parameters) - 1)
            )
            best_index = -1

            for i in hrange(len(self.parameters)):
                score = self.draw_parameter_score(i)
                if score > best_score:
                    best_score = score
                    best_index = i
            if best_index < 0:
                self.last_parameter_index = len(self.parameters)
                return self.new_parameter()
            self.last_parameter_index = best_index
            self.counts[self.last_parameter_index] += 1
            return self.parameters[self.last_parameter_index]

    def __iter__(self):
        self.started = True
        if self.storage is not None:
            for example in self.storage.fetch():
                self.mark_set = False
                yield example

        if self.strategy is not None:
            while True:
                parameter = self.pick_a_parameter()
                yield self.strategy.produce(
                    self.random, parameter
                )
