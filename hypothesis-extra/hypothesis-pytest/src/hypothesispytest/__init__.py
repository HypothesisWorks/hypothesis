# coding=utf-8

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# Most of this work is copyright (C) 2013-2015 David R. MacIver
# (david@drmaciver.com), but it contains contributions by other. See
# https://github.com/DRMacIver/hypothesis/blob/master/CONTRIBUTING.rst for a
# full list of people who may hold copyright, and consult the git log if you
# need to determine who owns an individual contribution.

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

import pytest


class StoringReporter(object):

    def __init__(self):
        self.results = []

    def __call__(self, msg):
        self.results.append(msg)


@pytest.mark.hookwrapper
def pytest_pyfunc_call(pyfuncitem):
    from hypothesis.reporting import with_reporter
    store = StoringReporter()
    with with_reporter(store):
        yield
    if store.results:
        pyfuncitem.hypothesis_report_information = list(store.results)


@pytest.mark.tryfirst
def pytest_runtest_makereport(item, call, __multicall__):
    report = __multicall__.execute()
    if hasattr(item, 'hypothesis_report_information'):
        report.sections.append((
            'Hypothesis',
            '\n'.join(item.hypothesis_report_information)
        ))
    return report


def load():
    pass
