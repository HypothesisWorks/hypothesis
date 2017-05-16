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
import re
import sys
from datetime import datetime, timedelta

import hypothesistooling as tools

sys.path.append(os.path.dirname(__file__))  # noqa


def version_string(nums):
    return '.'.join(str(s) for s in nums)


def version_nums(string):
    string = string.strip().split()[0]
    return tuple(int(n) for n in string.split('.'))


if __name__ == '__main__':

    if not tools.has_source_changes():
        print('No source changes found')
        sys.exit(0)

    found_problem = False

    now = datetime.utcnow()
    hour = timedelta(hours=1)
    acceptable_lines = sorted(set(
        '{} - {}'.format(tools.__version__, d.strftime('%Y-%m-%d'))
        for d in (now, now + hour, now - hour)
    ))

    pattern = r'\n\d+\.\d+\.\d+ - \d{4}-\d{2}-\d{2}\n'
    all_versions = list(map(str.strip, re.findall(pattern, tools.changelog())))
    v_nums = [version_nums(v) for v in all_versions]

    for line in acceptable_lines:
        if line == all_versions[0]:
            break
        elif line in all_versions:
            print('Changelog entry %r is not the first entry!  Check for '
                  'merge errors.' % line)
            found_problem = True
            break
    else:
        print('No line with version and current date (%s) in the changelog. '
              'Remember this will be released as soon as you merge to master!'
              % ' or '.join(repr(line) for line in acceptable_lines))
        found_problem = True

    for actual, expected in zip(v_nums, sorted(v_nums, reverse=True)):
        if actual != expected:
            print('Version order: expected %s, got %s' % (expected, actual))
            found_problem = True

    duplicates = sorted(set(v for v in v_nums if v_nums.count(v) > 1))
    if duplicates:
        plural = 's have' if len(duplicates) > 1 else ' has'
        entries = ', '.join(repr(version_string(v)) for v in duplicates)
        print('The following version%s multiple entries in the '
              'changelog: %s' % (plural, entries))
        found_problem = True

    skipped = []
    for this, last in zip(v_nums, v_nums[1:]):
        maj, minor, patch = last
        if maj <= 1:
            break
        next_patch, next_minor = (maj, minor, patch + 1), (maj, minor + 1, 0)
        if this not in (next_patch, next_minor, (maj + 1, 0, 0)):
            skipped.append('Version %r found after %r, expected %r or %r'
                           % tuple(version_string(v) for v in
                                   (this, last, next_patch, next_minor)))
            found_problem = True
    if skipped:
        print('\n'.join(skipped))

    sys.exit(int(found_problem))
