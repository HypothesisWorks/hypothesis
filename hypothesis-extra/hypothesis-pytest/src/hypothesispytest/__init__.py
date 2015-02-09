# coding=utf-8

# Copyright (C) 2013-2015 David R. MacIver (david@drmaciver.com)

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

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
        pyfuncitem.hypothesis_falsifying_example = store.results[-1]


@pytest.mark.tryfirst
def pytest_runtest_makereport(item, call, __multicall__):
    report = __multicall__.execute()
    if hasattr(item, 'hypothesis_falsifying_example'):
        report.sections.append((
            'Hypothesis',
            item.hypothesis_falsifying_example
        ))
    return report


def load():
    pass
