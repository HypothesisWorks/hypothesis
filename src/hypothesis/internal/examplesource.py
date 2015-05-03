# coding=utf-8

# Copyright (C) 2013-2015 David R. MacIver (david@drmaciver.com)

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

from __future__ import division, print_function, absolute_import, \
    unicode_literals


class ParameterSource(object):

    """An object that provides you with an a stream of parameters to work with.

    After being provided with a parameter, either by iterating or through use
    of pick_a_parameter() you can call mark_bad() to request fewer instances of
    that parameter in future.

    The algorithm used is variant Thompson Sampling with a bunch of additional
    heuristics and special cases to attempt to drive towards both novelty and
    reliability.

    """

    def __init__(
        self,
        context, strategy,
        min_parameters=25, min_tries=2,
        start_invalidating_at=5,
        invalidation_threshold=0.75,
        max_tries=None,
    ):
        if max_tries is None:
            max_tries = 50
        random = context.random
        self.context = context
        self.strategy = strategy
        self.max_tries = max_tries
        min_tries = min(min_tries, max_tries)
        self.random = random
        self.parameters = []
        self.last_parameter_index = -1
        self.last_but_one_parameter_index = -1
        self.min_parameters = min_parameters
        self.start_invalidating_at = start_invalidating_at
        self.invalidation_threshold = invalidation_threshold
        self.min_tries = min_tries
        self.bad_counts = []
        self.counts = []
        self.total_count = 0
        self.total_bad_count = 0
        self.mark_set = False
        self.started = False
        self.valid_parameters = []

    def mark_bad(self):
        """The last example was bad.

        If possible can we have less of that please?

        """
        if not self.started:
            raise ValueError('No parameters have been generated yet')
        if self.mark_set:
            raise ValueError('This parameter has already been marked')
        self.mark_set = True
        self.total_bad_count += 1
        self.bad_counts[self.last_parameter_index] += 1

    def new_parameter(self):
        result = self.strategy.produce_parameter(self.random)
        self.parameters.append(result)
        self.bad_counts.append(0)
        self.counts.append(1)
        index = len(self.parameters) - 1
        self.valid_parameters.append(index)
        self.last_but_one_parameter_index = self.last_parameter_index
        self.last_parameter_index = index
        self.mark_set = False
        return result

    def draw_parameter(self, index):
        self.last_parameter_index = index
        self.mark_set = False
        self.counts[index] += 1
        return self.parameters[index]

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
        """Draw a parameter value, either picking one we've already generated
        or generating a new one.

        This is a modified form of Thompson sampling with a bunch of special
        cases designed around failure modes I found in practice.

        1. Once a parameter is generated, we try it self.min_tries times before
           we try anything else.
        2. If we have fewer than self.min_parameters already generated we will
           always generate a new parameter in preference to reusing an existing
           one.
        3. We then perform Thompson sampling on len(self.parameters) + 1 arms.
           Then final arm is given a score by randomly picking an existing arm
           and drawing a score from that. If this arm is picked we generate a
           new parameter. This means that we always have a probability of at
           least 1/(2n) of generating a new parameter, but means that we are
           less enthusiastic to explore novelty in cases where most parameters
           we've drawn are terrible.

        """
        self.total_count += 1
        if self.parameters and self.counts[-1] < self.min_tries:
            return self.draw_parameter(len(self.parameters) - 1)
        if len(self.parameters) < self.min_parameters:
            return self.new_parameter()
        else:
            best_score = self.draw_parameter_score(
                self.random.randint(0, len(self.parameters) - 1)
            )
            best_index = -1

            while self.valid_parameters:
                i = self.valid_parameters[-1]
                if self.counts[i] == self.bad_counts[i]:
                    self.valid_parameters.pop()
                else:
                    break

            to_invalidate = []
            for i in self.valid_parameters:
                if self.counts[i] >= self.max_tries:
                    to_invalidate.append(i)
                    continue

                if (
                    self.counts[i] >= self.start_invalidating_at and
                    self.bad_counts[i] >= (
                        self.invalidation_threshold * self.counts[i])
                ):
                    to_invalidate.append(i)
                    continue
                score = self.draw_parameter_score(i)
                if score > best_score:
                    best_score = score
                    best_index = i
            for i in to_invalidate:
                self.valid_parameters.remove(i)
            if best_index < 0:
                return self.new_parameter()
            else:
                return self.draw_parameter(best_index)

    def __iter__(self):
        self.started = True
        while True:
            yield self.pick_a_parameter()

    def examples(self):
        self.started = True
        while True:
            p = self.pick_a_parameter()
            template = self.strategy.draw_template(
                self.context, p
            )
            yield self.strategy.reify(template)
