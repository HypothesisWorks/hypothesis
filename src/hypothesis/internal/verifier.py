# coding=utf-8

# Copyright (C) 2013-2015 David R. MacIver (david@drmaciver.com)

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

"""The main entry point for Hypothesis, providing the falsify method and all
the various errors it may throw."""

from __future__ import division, print_function, absolute_import, \
    unicode_literals

import time
from random import Random
from itertools import islice

import hypothesis.settings as hs
from hypothesis.extra import load_entry_points
from hypothesis.errors import Flaky, Timeout, Exhausted, Unfalsifiable, \
    Unsatisfiable, UnsatisfiedAssumption
from hypothesis.internal.tracker import Tracker
from hypothesis.internal.reflection import function_digest
from hypothesis.internal.examplesource import ParameterSource
from hypothesis.searchstrategy.strategies import BuildContext, strategy


class Verifier(object):

    """A wrapper object holding state required for a falsify invocation."""

    def __init__(
            self,
            random=None,
            settings=None,
    ):
        if settings is None:
            settings = hs.Settings.default
        self.settings = settings
        self.database = settings.database

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

    def falsify(
            self, hypothesis,
            *argument_types,
            **kwargs
    ):  # pylint: disable=too-many-locals,too-many-branches
        """
        Attempt to construct an example tuple x matching argument_types such
        that hypothesis(*x) returns a falsey value
        """
        teardown_example = kwargs.get('teardown_example') or (lambda x: None)
        setup_example = kwargs.get('setup_example') or (lambda: None)
        random = self.random
        if random is None:
            random = Random(
                function_digest(hypothesis)
            )

        build_context = BuildContext(random)

        search_strategy = strategy(argument_types, self.settings)
        storage = None
        if self.database is not None:
            storage = self.database.storage_for(argument_types)

        def falsifies(args):  # pylint: disable=missing-docstring
            example = None
            try:
                try:
                    setup_example()
                    example = search_strategy.reify(args)
                    return not hypothesis(*example)
                except UnsatisfiedAssumption:
                    return False
            finally:
                teardown_example(example)

        track_seen = Tracker()
        falsifying_examples = []
        if storage:
            for example in storage.fetch():
                track_seen.track(example)
                if falsifies(example):
                    falsifying_examples = [example]
                break

        satisfying_examples = 0
        timed_out = False
        max_examples = self.max_examples
        min_satisfying_examples = self.min_satisfying_examples

        parameter_source = ParameterSource(
            context=build_context, strategy=search_strategy,
            min_parameters=max(2, int(float(max_examples) / 10))
        )
        start_time = time.time()

        def time_to_call_it_a_day():
            """Have we exceeded our timeout?"""
            if self.timeout <= 0:
                return False
            return time.time() >= start_time + self.timeout

        for parameter in islice(
            parameter_source, max_examples - len(track_seen)
        ):
            if len(track_seen) >= search_strategy.size_upper_bound:
                break

            if falsifying_examples:
                break
            if time_to_call_it_a_day():
                break

            args = search_strategy.produce_template(
                build_context, parameter
            )

            if track_seen.track(args) > 1:
                parameter_source.mark_bad()
                continue
            try:
                setup_example()
                a = search_strategy.reify(args)
                try:
                    is_falsifying_example = not hypothesis(*a)
                finally:
                    teardown_example(a)
            except UnsatisfiedAssumption:
                parameter_source.mark_bad()
                continue
            satisfying_examples += 1
            if is_falsifying_example:
                falsifying_examples.append(args)
        run_time = time.time() - start_time
        timed_out = self.timeout >= 0 and run_time >= self.timeout
        if not falsifying_examples:
            if len(track_seen) >= search_strategy.size_lower_bound:
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


load_entry_points()
