#!/usr/bin/env python3

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

import os
import re
import sys
from subprocess import PIPE, run
from collections import defaultdict
from distutils.version import StrictVersion

import hypothesistooling as tools


class FailingExample(object):

    def __init__(self, chunk):
        """Turn a chunk of text into an object representing the test."""
        location, *lines = [l + '\n' for l in chunk.split('\n') if l.strip()]
        self.location = location.strip()
        pattern = 'File "(.+?)", line (\d+?), in .+'
        file, line = re.match(pattern, self.location).groups()
        self.file = os.path.join('docs', file)
        self.line = int(line) + 1
        got = lines.index('Got:\n')
        self.expected_lines = lines[lines.index('Expected:\n') + 1:got]
        self.got_lines = lines[got + 1:]
        self.checked_ok = None
        self.adjust()

    @property
    def indices(self):
        return slice(self.line, self.line + len(self.expected_lines))

    def adjust(self):
        with open(self.file) as f:
            lines = f.readlines()
        # The raw line number is the first line of *input*, so adjust to
        # first line of output by skipping lines which start with a prompt
        while self.line < len(lines):
            if lines[self.line].strip()[:4] not in ('>>> ', '... '):
                break
            self.line += 1
        # Sadly the filename and line number for doctests in docstrings is
        # wrong - see https://github.com/sphinx-doc/sphinx/issues/4223
        # Luckily, we can just cheat because they're all in one file for now!
        # (good luck if this changes without an upstream fix...)
        if lines[self.indices] != self.expected_lines:
            self.file = 'src/hypothesis/strategies.py'
            with open(self.file) as f:
                lines = f.readlines()
            self.line = 0
            while self.expected_lines[0] in lines:
                self.line = lines[self.line:].index(self.expected_lines[0])
                if lines[self.indices] == self.expected_lines:
                    break
        # Finally, set the flag for location quality
        self.checked_ok = lines[self.indices] == self.expected_lines

    def __repr__(self):
        return '{}\nExpected: {!r:.60}\nGot:      {!r:.60}'.format(
            self.location, self.expected, self.got)


def get_doctest_output():
    # Return a dict of filename: list of examples, sorted from last to first
    # so that replacing them in sequence works
    command = run(['sphinx-build', '-b', 'doctest', 'docs', 'docs/_build'],
                  stdout=PIPE, stderr=PIPE, encoding='utf-8')
    output = [FailingExample(c) for c in command.stdout.split('*' * 70)
              if c.strip().startswith('File "')]
    if not all(ex.checked_ok for ex in output):
        broken = '\n'.join(ex.location for ex in output if not ex.checked_ok)
        print('Could not find some tests:\n' + broken)
        sys.exit(1)
    tests = defaultdict(set)
    for ex in output:
        tests[ex.file].add(ex)
    return {fname: sorted(examples, key=lambda x: x.line, reverse=True)
            for fname, examples in tests.items()}


def main():
    os.chdir(tools.ROOT)
    version = run(['sphinx-build', '--version'], stdout=PIPE,
                  encoding='utf-8').stdout.lstrip('sphinx-build ')
    if StrictVersion(version) < '1.7':
        print('This script requires Sphinx 1.7 or later; got %s.\n' % version)
        sys.exit(2)
    failing = get_doctest_output()
    if not failing:
        print('All doctests are OK')
        sys.exit(0)
    if tools.has_uncommitted_changes('.'):
        print('Cannot fix doctests in place with uncommited changes')
        sys.exit(1)

    for fname, examples in failing.items():
        with open(fname) as f:
            lines = f.readlines()
        for ex in examples:
            lines[ex.indices] = ex.got_lines
        with open(fname, 'w') as f:
            f.writelines(lines)

    still_failing = get_doctest_output()
    if still_failing:
        print('Fixes failed: script broken or flaky tests.\n', still_failing)
        sys.exit(1)
    print('All failing doctests have been fixed.')
    sys.exit(0)


if __name__ == '__main__':
    main()
