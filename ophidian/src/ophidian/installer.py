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
import subprocess

import attr
from ophidian.utils import randhex

# Courtesy of mattip grepping the pypy release notes.
# TODO: Use this to support micro restrictions on pypy
PYPY_LANGUAGE_MAPPINGS = [
    ('1.5', '2.7.1'),
    ('1.8', '2.7.2'),
    ('2.0', '2.7.3'),
    ('2.3', '2.7.6'),
    ('2.4', '2.7.8'),
    ('2.5', '2.7.9'),
    ('2.6', '2.7.10'),
    ('5.6', '2.7.12'),
    ('5.7', '2.7.13'),
]


@attr.s
class AvailableVersion(object):
    identifier = attr.ib()
    major = attr.ib()
    minor = attr.ib()
    micro = attr.ib()
    implementation = attr.ib()


class Installer(object):
    pass


CPYTHON_PREFIX = 'cpython-'
PYPY_PREFIX = 'pypy-'


class BadInstallSpec(Exception):
    pass


def version_regex(major, minor, micro):
    parts = ['^']

    if major is None:
        major = r"\d"
    if minor is None:
        minor = r"\d"
    parts.append('%s.%s' % (major, minor))
    if micro is None:
        parts.append(r"(\.\d+)?")
    elif micro is 0:
        parts.append(r"(\.0)?")
    else:
        parts.append(r"\.%d" % (micro,))
    parts.append('$')
    return re.compile(''.join(parts))


class PyenvInstaller(Installer):
    def __init__(self, pyenv_root, installation_directory):
        self.__pyenv_root = pyenv_root
        self.__installation_directory = installation_directory
        self.__cached_definitions = None

    def install(
        self, major=None, minor=None, micro=None, implementation=None,
        identifier=None
    ):
        target = os.path.join(self.__installation_directory, randhex(16))

        if identifier is not None:
            if identifier.startswith(CPYTHON_PREFIX):
                self.__install(identifier[len(CPYTHON_PREFIX):], target)
            elif identifier.startswith(PYPY_PREFIX):
                self.__install(
                    'pypy-portable-' + identifier[len(PYPY_PREFIX):],
                    target
                )
            else:
                raise BadInstallSpec(
                    "I don't know how to install identifier %s" % (
                        identifier,))
        elif implementation == 'pypy':
            self.__install(
                max(
                    d for d in self.__definitions
                    if d.startswith('pypy-portable')), target,
            )
        else:
            definitions = self.__definitions
            regex = version_regex(
                major=major, minor=minor, micro=micro
            )
            matching_definitions = [d for d in definitions if regex.match(d)]
            if not matching_definitions:
                raise BadInstallSpec(
                    'No definitions matching %r' % (regex.pattern,))
            self.__install(max(matching_definitions), target)
        return os.path.join(target, 'bin', 'python')

    @property
    def __definitions(self):
        if self.__cached_definitions is None:
            self.__cached_definitions = tuple(sorted(
                l.decode('ascii') for l in
                subprocess.check_output(
                    [self.__binary, '--definitions']).split(b"\n")))
        return self.__cached_definitions

    def __install(self, identifier, path, configure_opts=None):
        env = dict(os.environ)

        if configure_opts is not None:
            env['PYTHON_CONFIGURE_OPTS'] = configure_opts

        subprocess.check_call([
            self.__binary, identifier, path
        ], stdout=sys.stderr)

    @property
    def __binary(self):
        return os.path.join(
            self.__pyenv_root, 'plugins', 'python-build', 'bin',
            'python-build'
        )
