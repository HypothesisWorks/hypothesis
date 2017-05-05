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

    if not tools.has_source_changes():
        print('No source changes found')
        sys.exit(0)

    now = datetime.utcnow()
    hour = timedelta(hours=1)
    acceptable_lines = sorted(set(
        '{} - {}'.format(tools.__version__, d.strftime('%Y-%m-%d'))
        for d in (now, now + hour, now - hour)
    ))

    for line in tools.changelog().split('\n'):
        if line.strip() in acceptable_lines:
            break
    else:
        print('No line with version and current date (%s) in the changelog. '
              'Remember this will be released as soon as you merge to master!'
              % ' or '.join(repr(line) for line in acceptable_lines))
        sys.exit(1)
