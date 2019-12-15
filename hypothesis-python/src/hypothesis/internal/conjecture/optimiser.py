# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Most of this work is copyright (C) 2013-2019 David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
# CONTRIBUTING.rst for a full list of people who may hold copyright, and
# consult the git log if you need to determine who owns an individual
# contribution.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.
#
# END HEADER

from __future__ import absolute_import, division, print_function

from hypothesis.internal.conjecture.data import ConjectureData, Status
from hypothesis.internal.conjecture.datatree import PreviouslyUnseenBehaviour
from hypothesis.internal.conjecture.engine import (
    BUFFER_SIZE,
    NO_SCORE,
    GenerationParameters,
)


class Optimiser(object):
    """A fairly basic optimiser designed to increase the value of scores for
    targeted property based testing.

    This implements a fairly naive hill climbing algorithm based on randomly
    regenerating parts of the test case to attempt to improve the result. It is
    not expected to produce amazing results, because it is designed to be run
    in a fairly small testing budget, so it prioritises finding easy wins and
    bailing out quickly if that doesn't work.

    For more information about targeted property-based testing, see
    Löscher, Andreas, and Konstantinos Sagonas. "Targeted property-based
    testing." Proceedings of the 26th ACM SIGSOFT International Symposium on
    Software Testing and Analysis. ACM, 2017.
    """

    def __init__(self, engine, data, target):
        self.engine = engine
        self.current_data = data
        self.target = target
        self.improved = False

    def run(self):
        self.hill_climb()

    def score_function(self, data):
        return data.target_observations.get(self.target, NO_SCORE)

    @property
    def current_score(self):
        return self.score_function(self.current_data)

    @property
    def random(self):
        return self.engine.random

    def consider_new_test_data(self, data):
        """Consider a new data object as a candidate target. If it is better
        than the current one, return True."""
        if data.status < Status.VALID:
            return False
        score = self.score_function(data)
        if score < self.current_score:
            return False
        if score > self.current_score:
            self.improved = True
            self.current_data = data
            return True
        return False

    def consider_new_buffer(self, buffer):
        return self.consider_new_test_data(self.engine.cached_test_function(buffer))

    def hill_climb(self):
        """Run hill climbing. Our hill climbing algorithm relies on selecting
        an example to improve. We try multiple example selection strategies to
        try to find one that works well."""

        def last_example(d):
            """Select the last non-empty example. This is particularly good for
            lists and other things which implement a logic of continuing until
            some condition is made."""
            i = len(d.examples) - 1
            while d.examples[i].length == 0:
                i -= 1
            return i

        def random_non_empty(d):
            """Select any non-empty example, uniformly at random."""
            while True:
                i = self.random.randrange(0, len(d.examples))
                if d.examples[i].length > 0:  # pragma: no branch  # flaky coverage :/
                    return i

        self.do_hill_climbing(last_example)
        self.do_hill_climbing(random_non_empty)

    def do_hill_climbing(self, select_example):
        """The main hill climbing loop where we actually do the work: Take
        data, and attempt to improve its score for target. select_example takes
        a data object and returns an index to an example where we should focus
        our efforts."""

        # The basic design of this is that we assume that there is some
        # "important prefix" that starts off the test case and that we might
        # benefit from redrawing everything after that point. This is an
        # especially good assumption for stateful testing, but it's not an
        # unreasonable assumption for everything else too.
        #
        # This means that the basic neighbourhoods we consider are to pick some
        # prefix of the current point, keep that fixed, and regenerate the
        # remaining test case according to some parameter.
        parameter = GenerationParameters(self.random)

        # We keep running our hill climbing until we've got (fairly weak)
        # evidence that we're at a local maximum.
        max_failures = 10
        consecutive_failures = 0
        while (
            consecutive_failures < max_failures
            # Once we've hit and interesting target it's time to stop hill
            # climbing because we don't really care about maximizing the score
            # further.
            and self.current_data.status <= Status.VALID
        ):
            if self.attempt_to_improve(
                parameter=parameter, example_index=select_example(self.current_data)
            ):
                # If we succeeed at improving the score then we no longer have
                # any evidence that we're at a local maximum so we reset the
                # count.
                consecutive_failures = 0
            else:
                # If we've failed in our hill climbing attempt, this could be
                # for two reasons: We've not picked enough of the test case to
                # capture what is interesting about this, or our parameter is
                # not a good one for generating the extensions we want. We
                # reset both of them in the hope of making more progress next
                # time around.
                parameter = GenerationParameters(self.random)
                consecutive_failures += 1

    def attempt_to_improve(self, example_index, parameter):
        """Part of our hill climbing implementation. Attempts to improve a
        given score by regenerating an example in the data based on a new
        parameter."""

        data = self.current_data
        self.current_score

        ex = data.examples[example_index]
        assert ex.length > 0
        prefix_size = ex.start
        prefix = data.buffer[:prefix_size]

        dummy = ConjectureData(
            prefix=prefix, parameter=parameter, max_length=BUFFER_SIZE,
        )
        try:
            self.engine.tree.simulate_test_function(dummy)
            # If this didn't throw an exception then we've already seen this
            # behaviour before and are trying something too similar to what
            # we already have.
            return False
        except PreviouslyUnseenBehaviour:
            pass

        attempt = self.engine.new_conjecture_data(
            prefix=dummy.buffer, parameter=parameter
        )
        self.engine.test_function(attempt)
        if self.consider_new_test_data(attempt):
            return True

        ex_attempt = attempt.examples[example_index]

        replacement = attempt.buffer[ex_attempt.start : ex_attempt.end]

        return self.consider_new_buffer(prefix + replacement + data.buffer[ex.end :])
