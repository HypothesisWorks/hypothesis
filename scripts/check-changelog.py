#!/usr/bin/env python

# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2017 David R. MacIver
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

import os
import sys
from datetime import datetime, timedelta

import hypothesistooling as tools

sys.path.append(os.path.dirname(__file__))  # noqa


if __name__ == '__main__':
    changelog = tools.changelog()

    if '\n%s - ' % (tools.__version__,) not in changelog:
        print(
            'The current version (%s) isn\'t mentioned in the changelog' % (
                tools.__version__,))
        sys.exit(1)

    now = datetime.utcnow()

    hour = timedelta(hours=1)

    acceptable_dates = {
        d.strftime('%Y-%m-%d')
        for d in (now, now + hour, now - hour)
    }

    when = ' or '.join(sorted(acceptable_dates))

    if not any(d in changelog for d in acceptable_dates):
        print((
            'The current date (%s) isn\'t mentioned in the changelog. '
            'Remember this will be released as soon as you merge to master!'
        ) % (when,))
        sys.exit(1)
