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

import logging

import pytest

from hypothesis import given, reporting
from hypothesis.strategies import integers


def test_log_messages_are_dropped_when_executing_each_nonfinal_case(caplog):
    # Setup a custom logger, and set the global minimum log level
    logger = logging.getLogger('hypothesis.test.test_logging.example')
    logging.disable(logging.INFO)

    # Setup a trivial test function
    @given(integers())
    def test(x):
        # This log message should always be dropped because of the global
        # `logging.disable()` setting
        logger.info('log info %d', x)

        # This log message should only appear in the final test case
        logger.warning('log warning %d', x)

        # The test case needs to fail otherwise there won't be a final test
        # case. Additionally, we want it to fail with a non-trivial minimal
        # example
        assert x < 10

    # Exercise
    with pytest.raises(AssertionError):
        with reporting.with_reporter(reporting.default):
            test()

    # Verify that only one log record was produced, even though we executed
    # multiple test cases
    assert len(caplog.records) == 1, \
        'Log messages from interim test executions should be suppressed'
    record = caplog.records[0]
    assert record.levelno == logging.WARNING, \
        'The log message at INFO level should be suppressed by the pre-set ' \
        'logging.disable() call'
    assert record.message == 'log warning 10', \
        'The log message should refer to the final test execution'
