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
from textwrap import dedent
from subprocess import PIPE, run
from collections import defaultdict
from distutils.version import StrictVersion

import hypothesistooling as tools
from hypothesistooling.scripts import tool_path

SPHINXBUILD = tool_path('sphinx-build')


def dedent_lines(lines, force_newline=None):
    """Remove common leading whitespace from a list of strings."""
    if not lines:
        return []
    joiner = '' if lines[0].endswith('\n') else '\n'
    lines = dedent(joiner.join(lines)).split('\n')
    if force_newline is False:
        return lines
    if force_newline is True:
        return [l + '\n' for l in lines]
    return [l + (bool(joiner) * '\n') for l in lines]


class FailingExample(object):

    def __init__(self, chunk):
        """Turn a chunk of text into an object representing the test."""
        # Determine and save the location of the actual doctest
        location, *lines = [l for l in chunk.split('\n') if l.strip()]
        self.location = location.strip()
        pattern = r'File "(.+?)", line (\d+|\?+), in .+'
        file, line = re.match(pattern, self.location).groups()
        self.file = os.path.join('docs', file)
        self.line = None if '?' in line else int(line)
        # Select the expected and returned output of the test
        got = lines.index('Got:')
        self.expected_lines = \
            dedent_lines(lines[lines.index('Expected:') + 1:got])
        self.got_lines = dedent_lines(lines[got + 1:])
        self.checked_ok = None
        self.adjust()

    @property
    def indices(self):
        return slice(self.line, self.line + len(self.expected_lines))

    def adjust(self):
        if self.line is None and self.file.endswith('.rst'):
            # Sphinx reports an unknown line number when the doctest is
            # included from a docstring, so docutils must have misreported the
            # file location.  We thus force it to the most likley candidate:
            self.file = 'src/hypothesis/strategies.py'
        with open(self.file) as f:
            lines = f.read().split('\n')
        if self.line is not None:
            # The raw line number is the first line of *input*, so adjust to
            # first line of output by skipping lines which start with a prompt
            while self.line < len(lines):
                if lines[self.line].lstrip()[:4] not in ('>>> ', '... '):
                    break
                self.line += 1
        else:
            # If the location within a file wasn't reported, we have to go
            # looking for it.
            stripped = [l.lstrip() for l in lines]
            self.line = 0
            while self.expected_lines[0] in stripped[self.line:]:
                self.line = stripped[self.line:].index(self.expected_lines[0])
                candidate = dedent_lines(lines[self.indices], False)
                if candidate == self.expected_lines:
                    break
                self.line += 1
        # Finally, set the flag for location quality
        self.checked_ok = \
            dedent_lines(lines[self.indices], False) == self.expected_lines

    def __repr__(self):
        return '{}\nExpected: {!r:.60}\nGot:      {!r:.60}'.format(
            self.location, self.expected_lines, self.got_lines)


def get_doctest_output():
    # Return a dict of filename: list of examples, sorted from last to first
    # so that replacing them in sequence works
    command = run([SPHINXBUILD, '-b', 'doctest', 'docs', 'docs/_build'],
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


def indent_like(lines, like):
    """Indent ``lines`` to the same level as ``like``."""
    prefix = len(like[0].rstrip()) - len(dedent_lines(like)[0].rstrip())
    return [prefix * ' ' + l for l in dedent_lines(lines, force_newline=True)]


def main():
    os.chdir(tools.ROOT)
    version = run([SPHINXBUILD, '--version'], stdout=PIPE,
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
            # Note: can't indent earlier, as we don't know file indentation
            lines[ex.indices] = indent_like(ex.got_lines, lines[ex.indices])
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
