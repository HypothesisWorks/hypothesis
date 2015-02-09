# coding=utf-8

# Copyright (C) 2013-2015 David R. MacIver (david@drmaciver.com)

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

"""The main entry point for Hypothesis, providing the falsify method and all
the various errors it may throw."""

from __future__ import division, print_function, unicode_literals

import time
from random import Random

import hypothesis.settings as hs
from hypothesis.extra import load_entry_points
from hypothesis.examplesource import ExampleSource
from hypothesis.strategytable import StrategyTable
from hypothesis.internal.tracker import Tracker
from hypothesis.database.converter import NotSerializeable
from hypothesis.internal.utils.reflection import function_digest, \
    get_pretty_function_description


def assume(condition):
    """Assert a precondition for this test.

    If this is not truthy then the test will abort but not fail and
    Hypothesis will make a "best effort" attempt to avoid similar
    examples in future.

    """
    if not condition:
        raise UnsatisfiedAssumption()
    return True


class Verifier(object):

    """A wrapper object holding state required for a falsify invocation."""

    def __init__(
            self,
            strategy_table=None,
            random=None,
            settings=None,
    ):
        if settings is None:
            settings = hs.default
        self.database = settings.database
        self.strategy_table = strategy_table or StrategyTable()
        if self.database is not None:
            self.strategy_table = self.strategy_table.augment_with_examples(
                self.examples_for
            )

        self.min_satisfying_examples = settings.min_satisfying_examples
        self.max_examples = settings.max_examples
        self.timeout = settings.timeout
        if settings.derandomize and random:
            raise ValueError(
                'A verifier cannot both be derandomized and have a random '
                'generator')

        if settings.derandomize:
            self.random = None
        else:
            self.random = random or Random()
        self.max_regenerations = 0

    def examples_for(self, descriptor):
        try:
            storage = self.database.storage_for(descriptor)
        except NotSerializeable:
            return ()
        return tuple(storage.fetch())

    def falsify(
            self, hypothesis, *argument_types
    ):  # pylint: disable=too-many-locals,too-many-branches
        """
        Attempt to construct an example tuple x matching argument_types such
        that hypothesis(*x) returns a falsey value or throws an AssertionError
        """
        random = self.random
        if random is None:
            random = Random(
                function_digest(hypothesis)
            )

        search_strategy = (
            self.strategy_table.specification_for(argument_types))
        storage = None
        if self.database is not None:
            try:
                storage = self.database.storage_for(argument_types)
            except NotSerializeable:
                pass

        def falsifies(args):  # pylint: disable=missing-docstring
            try:
                return not hypothesis(*search_strategy.copy(args))
            except AssertionError:
                return True
            except UnsatisfiedAssumption:
                return False

        track_seen = Tracker()
        falsifying_examples = []
        examples_found = 0
        satisfying_examples = 0
        timed_out = False
        if argument_types:
            max_examples = self.max_examples
            min_satisfying_examples = self.min_satisfying_examples
        else:
            max_examples = 1
            min_satisfying_examples = 1

        example_source = ExampleSource(
            random=random, strategy=search_strategy, storage=storage,
            min_parameters=max(2, int(float(max_examples) / 10))
        )
        start_time = time.time()

        def time_to_call_it_a_day():
            """Have we exceeded our timeout?"""
            if self.timeout <= 0:
                return False
            return time.time() >= start_time + self.timeout

        examples_seen = 0
        # At present this loop will never exit normally . This needs proper
        # testing when "database only" mode becomes available but right now
        # it's not.
        for args in example_source:  # pragma: no branch
            assert search_strategy.could_have_produced(args)
            if examples_found >= search_strategy.size_upper_bound:
                break

            if falsifying_examples:
                break
            if examples_seen >= max_examples:
                break
            if time_to_call_it_a_day():
                break
            examples_seen += 1

            if track_seen.track(args) > 1:
                example_source.mark_bad()
                continue
            examples_found += 1
            try:
                is_falsifying_example = not hypothesis(
                    *search_strategy.copy(args))
            except AssertionError:
                is_falsifying_example = True
            except UnsatisfiedAssumption:
                example_source.mark_bad()
                continue
            satisfying_examples += 1
            if is_falsifying_example:
                falsifying_examples.append(args)
        run_time = time.time() - start_time
        timed_out = self.timeout >= 0 and run_time >= self.timeout

        if not falsifying_examples:
            if examples_found >= search_strategy.size_lower_bound:
                raise Exhausted(
                    hypothesis, satisfying_examples)
            elif satisfying_examples < min_satisfying_examples:
                if timed_out:
                    raise Timeout(hypothesis, satisfying_examples, run_time)
                else:
                    raise Unsatisfiable(
                        hypothesis, satisfying_examples, run_time)
            else:
                raise Unfalsifiable(hypothesis)

        for example in falsifying_examples:
            if not falsifies(example):
                raise Flaky(hypothesis, example)

        best_example = falsifying_examples[0]

        for simpler in search_strategy.simplify_such_that(
                best_example, falsifies
        ):
            best_example = simpler
            if time_to_call_it_a_day():
                break

        if storage is not None:
            storage.save(best_example)

        return best_example


def falsify(*args, **kwargs):
    """A convenience wrapper function for Verifier.falsify."""
    return Verifier(**kwargs).falsify(*args)


class HypothesisException(Exception):

    """Generic parent class for exceptions thrown by Hypothesis."""
    pass


class UnsatisfiedAssumption(HypothesisException):

    """An internal error raised by assume.

    If you're seeing this error something has gone wrong.

    """

    def __init__(self):
        super(UnsatisfiedAssumption, self).__init__('Unsatisfied assumption')


class Unfalsifiable(HypothesisException):

    """The hypothesis we have been asked to falsify appears to be always true.

    This does not guarantee that no counter-example exists, only that we
    were unable to find one.

    """

    def __init__(self, hypothesis, extra=''):
        super(Unfalsifiable, self).__init__(
            'Unable to falsify hypothesis %s%s' % (
                get_pretty_function_description(hypothesis), extra)
        )


class Exhausted(Unfalsifiable):

    """We appear to have considered the entire example space available before
    we ran out of time or number of examples.

    This does not guarantee that we have considered the whole example
    space (it could just be a bad search strategy) but it makes it
    pretty likely that this hypothesis is just always true.

    """

    def __init__(self, hypothesis, n_examples):
        super(Exhausted, self).__init__(
            hypothesis, ' exhausted parameter space after %d examples' % (
                n_examples,
            )
        )


class Unsatisfiable(HypothesisException):

    """We ran out of time or examples before we could find enough examples
    which satisfy the assumptions of this hypothesis.

    This could be because the function is too slow. If so, try upping
    the timeout. It could also be because the function is using assume
    in a way that is too hard to satisfy. If so, try writing a custom
    strategy or using a better starting point (e.g if you are requiring
    a list has unique values you could instead filter out all duplicate
    values from the list)

    """

    def __init__(self, hypothesis, examples, run_time):
        super(Unsatisfiable, self).__init__((
            'Unable to satisfy assumptions of hypothesis %s. ' +
            'Only %s examples found after %g seconds'
        ) % (
            get_pretty_function_description(hypothesis),
            str(examples),
            run_time))


class Flaky(HypothesisException):

    """
    This function appears to fail non-deterministically: We have seen it fail
    when passed this example at least once, but a subsequent invocation did not
    fail.

    Common causes for this problem are:
        1. The function depends on external state. e.g. it uses an external
           random number generator. Try to make a version that passes all the
           relevant state in from Hypothesis.
        2. The function is suffering from too much recursion and its failure
           depends sensitively on where it's been called from.
        3. The function is timing sensitive and can fail or pass depending on
           how long it takes. Try breaking it up into smaller functions which
           dont' do that and testing those instead.
    """

    def __init__(self, hypothesis, example):
        super(Flaky, self).__init__((
            'Hypothesis %r produces unreliable results: %r falsified it on the'
            ' first call but did not on a subsequent one'
        ) % (get_pretty_function_description(hypothesis), example))


class Timeout(Unsatisfiable):

    """We were unable to find enough examples that satisfied the preconditions
    of this hypothesis in the amount of time allotted to us."""


load_entry_points()
