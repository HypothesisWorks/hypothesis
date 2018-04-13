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

"""Module for obtaining various versions of Python.

Currently this is a thin shim around pyenv, but it would be nice to have
this work on Windows as well by using Anaconda (as our build already
does).
"""

from __future__ import division, print_function, absolute_import

import os
import subprocess

import hypothesistooling.scripts as scripts

HOME = os.environ['HOME']


def __python_executable(version):
    return os.path.join(scripts.SNAKEPIT, version, 'bin', 'python')


def python_executable(version):
    ensure_python(version)
    return __python_executable(version)


PYTHONS = set()


def ensure_python(version):
    if version in PYTHONS:
        return
    scripts.run_script('ensure-python.sh', version)
    assert os.path.exists(__python_executable(version))
    PYTHONS.add(version)


STACK = os.path.join(HOME, '.local', 'bin', 'stack')
GHC = os.path.join(HOME, '.local', 'bin', 'ghc')
SHELLCHECK = os.path.join(HOME, '.local', 'bin', 'shellcheck')


def ensure_stack():
    if os.path.exists(STACK):
        return
    subprocess.check_call('mkdir -p ~/.local/bin', shell=True)
    subprocess.check_call(
        'curl -L https://www.stackage.org/stack/linux-x86_64 '
        '| tar xz --wildcards --strip-components=1 -C $HOME'
        "/.local/bin '*/stack'", shell=True
    )


def ensure_ghc():
    if os.path.exists(GHC):
        return
    ensure_stack()
    subprocess.check_call([STACK, 'setup'])


def ensure_shellcheck():
    if os.path.exists(SHELLCHECK):
        return
    ensure_ghc()
    subprocess.check_call([STACK, 'install', 'shellcheck'])
