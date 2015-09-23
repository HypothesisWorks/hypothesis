# coding=utf-8

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# Most of this work is copyright (C) 2013-2015 David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
# https://github.com/DRMacIver/hypothesis/blob/master/CONTRIBUTING.rst for a
# full list of people who may hold copyright, and consult the git log if you
# need to determine who owns an individual contribution.

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

from __future__ import division, print_function, absolute_import

import pytest

PYTEST_VERSION = tuple(map(int, pytest.__version__.split('.')))
if PYTEST_VERSION >= (2, 7, 0):
    class StoringReporter(object):

        def __init__(self, config):
            self.config = config
            self.results = []

        def __call__(self, msg):
            if self.config.getoption('capture', 'fd') == 'no':
                print(msg)
            self.results.append(msg)

    @pytest.mark.hookwrapper
    def pytest_pyfunc_call(pyfuncitem):
        from hypothesis.reporting import with_reporter
        store = StoringReporter(pyfuncitem.config)
        with with_reporter(store):
            yield
        if store.results:
            pyfuncitem.hypothesis_report_information = list(store.results)

    @pytest.mark.hookwrapper
    def pytest_runtest_makereport(item, call):
        report = (yield).get_result()
        if hasattr(item, 'hypothesis_report_information'):
            report.sections.append((
                'Hypothesis',
                '\n'.join(item.hypothesis_report_information)
            ))

    def pytest_collection_modifyitems(items):
        for item in items:
            if not isinstance(item, pytest.Function):
                continue
            if getattr(item.function, 'is_hypothesis_test', False):
                item.add_marker('hypothesis')

    def load():
        pass
