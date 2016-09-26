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
import threading

import pytest
import _pytest.runner as runner
from _pytest.python import Function

from hypothesis import given
from hypothesis.reporting import default as default_reporter
from hypothesis.reporting import with_reporter
from hypothesis.statistics import collector
from hypothesis.internal.compat import ArgSpec, text_type, OrderedDict
from hypothesis.internal.detection import is_hypothesis_test
from hypothesis.internal.reflection import impersonate, copy_argspec
from hypothesis.internal.conjecture.data import StopTest

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
                '  - Stopped because %s' % (statistics.exit_reason,)
            )
            if statistics.events:
                terminalreporter.write_line('  - Events:')
                for event in statistics.events:
                    terminalreporter.write_line(
                        '    * %s' % (event,)
                    )
            terminalreporter.write_line('')

    class PytestReportedAsFailed(Exception):
        """Internal exception class to indicate to given that a test is a
        failure."""

    report_storage = threading.local()

    @pytest.hookimpl(tryfirst=True)
    def pytest_runtest_protocol(item, nextitem):
        if isinstance(item, Function) and is_hypothesis_test(item.function):
            report_storage.last_report = []
            runner.runtestprotocol(item, nextitem=nextitem, log=False)
            item.ihook.pytest_runtest_logstart(
                nodeid=item.nodeid, location=item.location,
            )
            for report in report_storage.last_report:
                item.ihook.pytest_runtest_logreport(report=report)
            return True

    def convert_given(item):
        original_item = item
        given_kwargs = item.function._hypothesis_internal_use_kwargs
        unwrapped_test = \
            item.function._hypothesis_internal_use_original_test

        @given(**given_kwargs)
        @impersonate(unwrapped_test)
        @copy_argspec(
            item.function.__name__,
            ArgSpec(sorted(given_kwargs), None, None, None),
        )
        def accept(**kwargs):
            item_for_unwrapped_test = type(original_item)(
                name=original_item.name,
                parent=original_item.parent,
                args=original_item._args,
                config=original_item.config,
                callobj=unwrapped_test,
                keywords=dict(original_item.keywords),
                session=original_item.session,
                originalname=original_item.originalname,
            )
            item_for_unwrapped_test.funcargs = {}
            for k, v in kwargs.items():
                item_for_unwrapped_test.funcargs[k] = v
            reports = runner.runtestprotocol(
                item_for_unwrapped_test, log=False, nextitem=None)
            report_storage.last_report = reports
            for r in reports:
                if r.failed:
                    raise PytestReportedAsFailed()

        item = type(item)(
            name=item.name,
            parent=item.parent,
            args=item._args,
            config=item.config,
            callobj=accept,
            keywords=dict(item.keywords),
            session=item.session,
            originalname=item.originalname,
        )
        item.add_marker('hypothesis')
        return item

    def pytest_collection_modifyitems(items):
        for i, item in enumerate(items):
            if not isinstance(item, pytest.Function):
                continue

            if is_hypothesis_test(item.function):
                items[i] = convert_given(item)

    def load():
        pass
