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

import hypothesistooling as tools

sys.path.append(os.path.dirname(__file__))  # noqa


if __name__ == '__main__':
    if tools.has_source_changes():
        if not tools.has_release():
            print(
                'There are source changes but no RELEASE.rst. Please create '
                'one to describe your changes.'
            )
            sys.exit(1)
        tools.parse_release_file()
