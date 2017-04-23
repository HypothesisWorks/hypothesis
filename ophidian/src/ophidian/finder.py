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
import glob
import json
import subprocess

import attr


VALID_PYTHON_NAMES = re.compile(r"""
    ^
    (python|pypy)  # We currently only support these two implementations
    (-?(\d\.?)+)?
    (\.exe)?
    $
""", re.VERBOSE)


def is_valid_python_name(name):
    return VALID_PYTHON_NAMES.match(name) is not None


@attr.s
class Python(object):
    path = attr.ib()
    version = attr.ib()
    implementation = attr.ib()
    wide = attr.ib()
    wordsize = attr.ib()
    mtime = attr.ib()

    @property
    def stale(self):
        return os.stat(self.path).st_mtime != self.mtime


EXTRA_PATHS = [os.path.expanduser('~/bin')]


def default_paths():
    paths = list(os.environ['PATH'].split(os.pathsep) + EXTRA_PATHS)

    paths.extend(
        glob.glob(os.path.expanduser('~/.pyenv/versions/*/bin'))
    )
    return paths


SYSTEM_CHECK_FILE = os.path.join(os.path.dirname(__file__), 'systemcheck.py')


def python_for_exe(path):
    output = subprocess.check_output([path, SYSTEM_CHECK_FILE])
    params = json.loads(output)
    params['version'] = tuple(params['version'])
    params['path'] = path
    params['mtime'] = os.stat(path).st_mtime
    return Python(**params)


def looks_pythonic(path):
    if not os.access(path, os.X_OK):
        # We can't execute this file
        return False

    with open(path, 'rb') as i:
        header = i.read(2)
        if len(header) != 2:
            # File too small
            return False
        elif header == b'#!':
            # Has a shebang, probably not what we want.
            return False
    return True


def find_pythons(paths=None, skip_path=None):
    if paths is None:
        paths = default_paths()

    if skip_path is None:
        def skip_path(path): return False

    seen = set()

    for location in paths:
        if not os.path.isdir(location):
            continue
        for child in os.listdir(location):
            if not is_valid_python_name(child):
                continue
            path = os.path.realpath(os.path.join(location, child))
            if path in seen:
                continue
            seen.add(path)
            if skip_path(path):
                continue
            if not looks_pythonic(path):
                continue
            yield python_for_exe(path)
