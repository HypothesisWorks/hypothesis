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
from _pytest.fixtures import FuncFixtureInfo

from hypothesis import given
from hypothesis.errors import UnsatisfiedAssumption
from hypothesis.reporting import default as default_reporter
from hypothesis.reporting import with_reporter
from hypothesis.statistics import collector
from hypothesis.internal.compat import ArgSpec, text_type, getargspec, \
    OrderedDict
from hypothesis.internal.detection import is_hypothesis_test
from hypothesis.internal.reflection import proxies, impersonate, \
    copy_argspec
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

    report_storage = threading.local()

    @pytest.hookimpl(tryfirst=True)
    def pytest_runtest_protocol(item, nextitem):
        if isinstance(item, Function) and is_hypothesis_test(item.function):
            report_storage.last_report = []
            result = runner.runtestprotocol(item, nextitem=nextitem, log=False)
            item.ihook.pytest_runtest_logstart(
                nodeid=item.nodeid, location=item.location,
            )
            for report in (report_storage.last_report or result):
                item.ihook.pytest_runtest_logreport(report=report)
            return True

    class PytestFailedInternal(Exception):
        pass

    def convert_given(item):
        """Takes a Function test item that uses given, takes it apart and puts
        it back together in a way so that pytest fixtures are instantiated on
        every call to the function."""
        original_item = item
        given_kwargs = item.function._hypothesis_internal_use_kwargs
        unwrapped_test = \
            item.function._hypothesis_internal_use_original_test

        captured_exception = [None]

        @proxies(unwrapped_test)
        def call_test_and_capture_exception(*args, **kwargs):
            captured_exception[0] = None
            try:
                unwrapped_test(*args, **kwargs)
            except BaseException as e:
                captured_exception[0] = e
                raise e

        try:
            call_test_and_capture_exception.parametrize = item.function.parametrize
        except AttributeError:
            pass

        original_fi = original_item._fixtureinfo
        args = getargspec(unwrapped_test).args
        fixtureinfo = FuncFixtureInfo(
            argnames=args,
            names_closure=sorted(set(original_fi.names_closure) | set(args)),
            name2fixturedefs=original_fi.name2fixturedefs,
        )

        @given(**given_kwargs)
        @impersonate(unwrapped_test)
        @copy_argspec(
            item.function.__name__,
            ArgSpec(sorted(given_kwargs), None, None, None),
        )
        def accept(**kwargs):
            item_kwargs = dict(
                name=original_item.name,
                parent=original_item.parent,
                args=original_item._args,
                config=original_item.config,
                callobj=call_test_and_capture_exception,
                keywords=dict(original_item.keywords),
                session=original_item.session,
                originalname=original_item.originalname,
                fixtureinfo=fixtureinfo,
            )
            try:
                item_kwargs['callspec'] = original_item.callspec
            except AttributeError:
                pass

            item_for_unwrapped_test = type(original_item)(**item_kwargs)

            for k, v in kwargs.items():
                item_for_unwrapped_test.funcargs[k] = v

            reports = runner.runtestprotocol(
                item_for_unwrapped_test, log=False, nextitem=None)
            report_storage.last_report = reports
            if captured_exception[0] is not None:
                raise captured_exception[0]
            else:
                if any(r.failed for r in reports):
                    raise PytestFailedInternal()

        assert getargspec(accept).args == []

        item = type(item)(
            name=item.name,
            parent=item.parent,
            callobj=accept,
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
