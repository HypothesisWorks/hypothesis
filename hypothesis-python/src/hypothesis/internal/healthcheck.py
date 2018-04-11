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

from hypothesis.errors import FailedHealthCheck


def fail_health_check(settings, message, label):
    # Tell pytest to omit the body of this function from tracebacks
    # http://doc.pytest.org/en/latest/example/simple.html#writing-well-integrated-assertion-helpers
    __tracebackhide__ = True

    if label in settings.suppress_health_check:
        return
    if not settings.perform_health_check:
        return
    message += (
        '\nSee https://hypothesis.readthedocs.io/en/latest/health'
        'checks.html for more information about this. '
        'If you want to disable just this health check, add %s '
        'to the suppress_health_check settings for this test.'
    ) % (label,)
    raise FailedHealthCheck(message, label)
