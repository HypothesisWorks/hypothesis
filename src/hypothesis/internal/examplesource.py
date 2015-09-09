from __future__ import division, print_function, absolute_import


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
        random, strategy, max_tries=None,
    ):
        self.max_tries = max_tries or 10
        self.random = random
        self.strategy = strategy
        self.new_parameter()
        self.started = False
        self.mark_set = False
        self.should_switch = False
        self.count = 0

    def mark_bad(self):
        """The last example was bad.

        If possible can we have less of that please?

        """
        if not self.started:
            raise ValueError(u'No parameters have been generated yet')
        if self.mark_set:
            raise ValueError(u'This parameter has already been marked')
        self.should_switch = True
        self.mark_set = True

    def new_parameter(self):
        self.count = 0
        self.should_switch = False
        self.current_parameter = self.strategy.draw_parameter(self.random)
        return self.current_parameter

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
        self.started = True
        self.mark_set = False
        if self.should_switch or self.count >= self.max_tries:
            return self.new_parameter()
        else:
            self.count += 1
            return self.current_parameter

    def __iter__(self):
        self.started = True
        while True:
            yield self.pick_a_parameter()

    def examples(self):
        self.started = True
        while True:
            p = self.pick_a_parameter()
            template = self.strategy.draw_template(
                self.random, p
            )
            yield self.strategy.reify(template)
