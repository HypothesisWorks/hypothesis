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


def should_format_file(path):
    if os.path.basename(path) in ('header.py', 'test_lambda_formatting.py'):
        return False
    if 'vendor' in path.split(os.path.sep):
        return False
    return path.endswith('.py')


if __name__ == '__main__':
    changed = tools.modified_files()

    format_all = os.environ.get('FORMAT_ALL', '').lower() == 'true'
    if 'scripts/header.py' in changed:
        # We've changed the header, so everything needs its header updated.
        format_all = True
    if 'requirements/tools.txt' in changed:
        # We've changed the tools, which includes a lot of our formatting
        # logic, so we need to rerun formatters.
        format_all = True

    files = tools.all_files() if format_all else changed

    for f in sorted(files):
        if should_format_file(f):
            print(f)
