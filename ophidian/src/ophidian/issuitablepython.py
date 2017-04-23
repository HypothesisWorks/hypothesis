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

# We run this script as a system check to see if a version of Python is
# adequate for our purposes.

from __future__ import division, print_function, absolute_import

import sys

import pip  # noqa
# We need virtualenv and pip to be installed so we import them here as a check
import virtualenv  # noqa

if __name__ == '__main__':
    version = sys.version_info[:2]
    if version < (2, 7):
        sys.exit(1)
    elif (3, 0) <= version <= (3, 3):
        sys.exit(1)
    else:
        sys.exit(0)
