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

import re

import pytest

from hypothesis.reporting import default as default_reporter
from hypothesis.reporting import with_reporter
from hypothesis.statistics import collector
from hypothesis.internal.compat import text_type, OrderedDict
from hypothesis.internal.detection import is_hypothesis_test

PYTEST_VERSION = tuple(map(
    int,
    re.sub('-.+', '', pytest.__version__).split('.')[:3]
))

LOAD_PROFILE_OPTION = '--hypothesis-profile'
PRINT_STATISTICS_OPTION = '--hypothesis-show-statistics'

if PYTEST_VERSION >= (2, 7, 0):
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

    def pytest_configure(config):
        from hypothesis import settings
        profile = config.getoption(LOAD_PROFILE_OPTION)
        if profile:
            settings.load_profile(profile)

    gathered_statistics = OrderedDict()

    @pytest.mark.hookwrapper
    def pytest_runtest_call(item):
        if not hasattr(item, 'function'):
            yield
        elif not is_hypothesis_test(item.function):
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
