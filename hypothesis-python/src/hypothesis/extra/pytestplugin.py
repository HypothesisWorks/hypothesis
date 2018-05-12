# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2018 David R. MacIver
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

import pytest

import hypothesis.core as core
from hypothesis.reporting import default as default_reporter
from hypothesis.reporting import with_reporter
from hypothesis.statistics import collector
from hypothesis.internal.compat import OrderedDict, text_type
from hypothesis.internal.detection import is_hypothesis_test

LOAD_PROFILE_OPTION = '--hypothesis-profile'
PRINT_STATISTICS_OPTION = '--hypothesis-show-statistics'
SEED_OPTION = '--hypothesis-seed'


class StoringReporter(object):

    def __init__(self, config):
        self.config = config
        self.results = []

    def __call__(self, msg):
        if self.config.getoption('capture', 'fd') == 'no':
            default_reporter(msg)
        if not isinstance(msg, text_type):
            msg = repr(msg)
        self.results.append(msg)


def pytest_addoption(parser):
    group = parser.getgroup('hypothesis', 'Hypothesis')
    group.addoption(
        LOAD_PROFILE_OPTION,
        action='store',
        help='Load in a registered hypothesis.settings profile'
    )
    group.addoption(
        PRINT_STATISTICS_OPTION,
        action='store_true',
        help='Configure when statistics are printed',
        default=False
    )
    group.addoption(
        SEED_OPTION,
        action='store',
        help='Set a seed to use for all Hypothesis tests'
    )


def pytest_configure(config):
    core.running_under_pytest = True
    from hypothesis import settings
    profile = config.getoption(LOAD_PROFILE_OPTION)
    if profile:
        settings.load_profile(profile)
    seed = config.getoption(SEED_OPTION)
    if seed is not None:
        try:
            seed = int(seed)
        except ValueError:
            pass
        core.global_force_seed = seed
    config.addinivalue_line(
        'markers',
        'hypothesis: Tests which use hypothesis.')


gathered_statistics = OrderedDict()


@pytest.mark.hookwrapper
def pytest_runtest_call(item):
    if not (hasattr(item, 'obj') and is_hypothesis_test(item.obj)):
        yield
    else:
        store = StoringReporter(item.config)

        def note_statistics(stats):
            gathered_statistics[item.nodeid] = stats

        with collector.with_value(note_statistics):
            with with_reporter(store):
                yield
        if store.results:
            item.hypothesis_report_information = list(store.results)


@pytest.mark.hookwrapper
def pytest_runtest_makereport(item, call):
    report = (yield).get_result()
    if hasattr(item, 'hypothesis_report_information'):
        report.sections.append((
            'Hypothesis',
            '\n'.join(item.hypothesis_report_information)
        ))


def pytest_terminal_summary(terminalreporter):
    if not terminalreporter.config.getoption(PRINT_STATISTICS_OPTION):
        return
    terminalreporter.section('Hypothesis Statistics')
    for name, statistics in gathered_statistics.items():
        terminalreporter.write_line(name + ':')
        terminalreporter.write_line('')

        if not statistics.has_runs:
            terminalreporter.write_line('  - Test was never run')
            continue

        terminalreporter.write_line((
            '  - %d passing examples, %d failing examples,'
            ' %d invalid examples') % (
            statistics.passing_examples, statistics.failing_examples,
            statistics.invalid_examples,
        ))
        terminalreporter.write_line(
            '  - Typical runtimes: %s' % (statistics.runtimes,)
        )
        terminalreporter.write_line(
            '  - Fraction of time spent in data generation: %s' % (
                statistics.draw_time_percentage,))
        terminalreporter.write_line(
            '  - Stopped because %s' % (statistics.exit_reason,)
        )
        if statistics.events:
            terminalreporter.write_line('  - Events:')
            for event in statistics.events:
                terminalreporter.write_line(
                    '    * %s' % (event,)
                )
        terminalreporter.write_line('')


def pytest_collection_modifyitems(items):
    for item in items:
        if not isinstance(item, pytest.Function):
            continue
        if getattr(item.function, 'is_hypothesis_test', False):
            item.add_marker('hypothesis')


def load():
    pass
