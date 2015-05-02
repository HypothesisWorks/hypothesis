# coding=utf-8

# Copyright (C) 2013-2015 David R. MacIver (david@drmaciver.com)

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

from __future__ import division, print_function, absolute_import, \
    unicode_literals

import time
import signal
from random import Random
from functools import wraps

from hypothesis import Settings, strategy
from hypothesis.core import find
from hypothesis.errors import NoExamples, UnsatisfiedAssumption
from hypothesis.database import ExampleDatabase
from hypothesis.internal.compat import hrange
from hypothesis.internal.tracker import Tracker


class Timeout(BaseException):
    pass


try:
    signal.SIGALRM
    # The tests here have a tendency to run away with themselves a it if
    # something goes wrong, so we use a relatively hard kill timeout.

    def timeout(seconds=1):
        def decorate(f):
            @wraps(f)
            def wrapped(*args, **kwargs):
                start = time.time()

                def handler(signum, frame):
                    raise Timeout(
                        'Timed out after %.2fs' % (time.time() - start))

                old_handler = signal.signal(signal.SIGALRM, handler)
                signal.alarm(seconds)
                try:
                    return f(*args, **kwargs)
                finally:
                    signal.signal(signal.SIGALRM, old_handler)
                    signal.alarm(0)
            return wrapped
        return decorate
except AttributeError:
    # We're on an OS with no SIGALRM. Fall back to no timeout.
    def timeout(seconds=1):
        def decorate(f):
            return f
        return decorate


quality_settings = Settings(
    max_examples=5000,
    max_shrinks=5000,
)


def minimal(definition, condition=None, settings=None, timeout_after=10):
    condition = condition or (lambda x: True)
    with settings or quality_settings:
        settings = Settings(timeout=timeout_after * 0.95)

    @timeout(timeout_after)
    def run():
        return find(
            definition,
            condition,
            settings=settings
        )
    return run()


def some_template(spec, random=None):
    if random is None:
        random = Random()
    strat = strategy(spec)
    for _ in hrange(10):
        element = strat.draw_and_produce_from_random(random)
        try:
            strat.reify(element)
            return element
        except UnsatisfiedAssumption:
            pass
    else:
        raise NoExamples('some_template called on strategy with no examples')


def via_database(spec, strat, template):
    db = ExampleDatabase()
    s = db.storage_for(strat, strat)
    s.save(template)
    results = list(s.fetch())
    assert len(results) == 1
    return results[0]


def minimal_element(strategy, random):
    tracker = Tracker()
    element = some_template(strategy, random)
    while True:
        for new_element in strategy.full_simplify(random, element):
            if tracker.track(new_element) > 1:
                continue
            try:
                strategy.reify(new_element)
                element = new_element
                break
            except UnsatisfiedAssumption:
                pass
        else:
            break
    return element


def minimal_elements(strategy, random):
    found = set()
    dupe_count = 0
    for _ in hrange(10):
        x = minimal_element(strategy, random)
        if x in found:
            dupe_count += 1
            if dupe_count > 1:
                break
        else:
            dupe_count = 0
            found.add(x)
    return frozenset(found)
