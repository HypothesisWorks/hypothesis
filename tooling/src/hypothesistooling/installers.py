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
from hypothesistooling import git

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
    target = __python_executable(version)
    assert os.path.exists(target), target
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


stack_updated = False


def update_stack():
    global stack_updated
    if stack_updated:
        return
    stack_updated = True
    ensure_stack()
    subprocess.check_call([STACK, 'update'])


def ensure_ghc():
    if os.path.exists(GHC):
        return
    update_stack()
    subprocess.check_call([STACK, 'setup'])


def ensure_shellcheck():
    if os.path.exists(SHELLCHECK):
        return
    update_stack()
    ensure_ghc()
    subprocess.check_call([STACK, 'install', 'ShellCheck'])


def ensure_rustup():
    scripts.run_script('ensure-rustup.sh')


RUBY_BUILD = os.path.join(scripts.RBENV_ROOT, 'plugins', 'ruby-build')

RUBY_BIN_DIR = os.path.join(scripts.INSTALLED_RUBY_DIR, 'bin')

BUNDLER_EXECUTABLE = os.path.join(RUBY_BIN_DIR, 'bundle')
GEM_EXECUTABLE = os.path.join(RUBY_BIN_DIR, 'gem')

RBENV_COMMAND = os.path.join(scripts.RBENV_ROOT, 'bin', 'rbenv')


def ensure_ruby():
    if not os.path.exists(scripts.RBENV_ROOT):
        git('clone', 'https://github.com/rbenv/rbenv.git', scripts.RBENV_ROOT)

    if not os.path.exists(RUBY_BUILD):
        git('clone', 'https://github.com/rbenv/ruby-build.git', RUBY_BUILD)

    if not os.path.exists(
        os.path.join(scripts.RBENV_ROOT, 'versions', scripts.RBENV_VERSION)
    ):
        subprocess.check_call(
            [RBENV_COMMAND, 'install', scripts.RBENV_VERSION])

    if not (
        os.path.exists(BUNDLER_EXECUTABLE) and
        subprocess.call([BUNDLER_EXECUTABLE, 'version']) == 0
    ):
        subprocess.check_call(
            [GEM_EXECUTABLE, 'install', 'bundler']
        )

    assert os.path.exists(BUNDLER_EXECUTABLE)
