# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2016 David R. MacIver
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

import traceback

from hypothesis import strategies as st
from hypothesis import event, given, example
from hypothesis.statistics import collector


def call_for_statistics(test_function):
    result = [None]

    def callback(statistics):
        result[0] = statistics

    with collector.with_value(callback):
        try:
            test_function()
        except:
            traceback.print_exc()
            pass
    assert result[0] is not None
    return result[0]


def test_can_callback_with_a_string():
    @given(st.integers())
    def test(i):
        event('hi')

    stats = call_for_statistics(test)

    assert any('hi' in s for s in stats.events)


counter = 0
seen = []


class Foo(object):

    def __eq__(self, other):
        return True

    def __ne__(self, other):
        return False

    def __hash__(self):
        return 0

    def __str__(self):
        seen.append(self)
        global counter
        counter += 1
        return 'COUNTER %d' % (counter,)


def test_formats_are_evaluated_only_once():
    global counter
    counter = 0

    @given(st.integers())
    def test(i):
        event(Foo())

    stats = call_for_statistics(test)

    assert any('COUNTER 1' in s for s in stats.events)
    assert not any('COUNTER 2' in s for s in stats.events)


def test_does_not_report_on_examples():
    @example('hi')
    @given(st.integers())
    def test(i):
        if isinstance(i, str):
            event('boo')

    stats = call_for_statistics(test)
    assert not any('boo' in e for e in stats.events)


timing = 0


def fake_time():
    global timing
    timing += 0.5
    return timing


def test_exact_timing(monkeypatch):
    import hypothesis.internal.conjecture.data as d
    monkeypatch.setattr(d, 'benchmark_time', fake_time)

    @given(st.integers())
    def test(i):
        pass

    stats = call_for_statistics(test)
    assert stats.runtimes == '~ 500ms'


def test_flaky_exit():
    first = [True]

    @given(st.integers())
    def test(i):
        if i > 1001:
            if first[0]:
                first[0] = False
                print('Hi')
                assert False

    stats = call_for_statistics(test)
    assert stats.exit_reason == 'test was flaky'
