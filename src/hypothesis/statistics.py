# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2017 David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
# CONTRIBUTING.rst for a full list of people who may hold copyright, and
# consult the git log if you need to determine who owns an individual
# contribution.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.
#
# END HEADER

from __future__ import division, print_function, absolute_import

import math

from hypothesis.utils.dynamicvariables import DynamicVariable
from hypothesis.internal.conjecture.data import Status
from hypothesis.internal.conjecture.engine import ExitReason

collector = DynamicVariable(None)


class Statistics(object):

    def __init__(self, engine):
        self.passing_examples = len(
            engine.status_runtimes.get(Status.VALID, ()))
        self.invalid_examples = len(
            engine.status_runtimes.get(Status.INVALID, []) +
            engine.status_runtimes.get(Status.OVERRUN, [])
        )
        self.failing_examples = len(engine.status_runtimes.get(
            Status.INTERESTING, ()))

        runtimes = sorted(
            engine.status_runtimes.get(Status.VALID, []) +
            engine.status_runtimes.get(Status.INVALID, []) +
            engine.status_runtimes.get(Status.INTERESTING, [])
        )

        self.has_runs = bool(runtimes)
        if not self.has_runs:
            return

        n = max(0, len(runtimes) - 1)
        lower = int(runtimes[int(math.floor(n * 0.05))] * 1000)
        upper = int(runtimes[int(math.ceil(n * 0.95))] * 1000)
        if upper == 0:
            self.runtimes = '< 1ms'
        elif lower == upper:
            self.runtimes = '~ %dms' % (lower,)
        else:
            self.runtimes = '%d-%d ms' % (lower, upper)

        if engine.exit_reason == ExitReason.finished:
            self.exit_reason = 'nothing left to do'
        elif engine.exit_reason == ExitReason.flaky:
            self.exit_reason = 'test was flaky'
        else:
            self.exit_reason = (
                'settings.%s=%r' % (
                    engine.exit_reason.name,
                    getattr(engine.settings, engine.exit_reason.name)
                )
            )

        self.events = [
            '%.2f%%, %s' % (
                c / engine.call_count * 100, e
            ) for e, c in sorted(
                engine.event_call_counts.items(), key=lambda x: -x[1])
        ]


def note_engine_for_statistics(engine):
    callback = collector.value
    if callback is not None:
        callback(Statistics(engine))
