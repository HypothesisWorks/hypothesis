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


RUBY_VERSION = '2.5.1'

RUBY_DIR = os.path.join(
    scripts.BASE, 'ruby-versions', RUBY_VERSION
)

RUBY_BIN_DIR = os.path.join(RUBY_DIR, 'bin')

RUBY_EXECUTABLE = os.path.join(RUBY_BIN_DIR, 'ruby')
GEM_EXECUTABLE = os.path.join(RUBY_BIN_DIR, 'gem')
BUNDLER_EXECUTABLE = os.path.join(RUBY_BIN_DIR, 'bundler')


RUBY_BUILD_DIR = os.path.join(scripts.BASE, 'ruby-build')

RUBY_BUILD = os.path.join(RUBY_BUILD_DIR, 'bin', 'ruby-build')


def ensure_ruby():
    if not os.path.exists(RUBY_BUILD_DIR):
        subprocess.check_call([
            'git', 'clone', 'https://github.com/rbenv/ruby-build.git',
            RUBY_BUILD_DIR
        ])

    assert os.path.exists(RUBY_BUILD_DIR)

    if not os.path.exists(RUBY_EXECUTABLE):
        subprocess.check_call([RUBY_BUILD, RUBY_VERSION, RUBY_DIR])

    assert os.path.exists(RUBY_EXECUTABLE)
    assert os.path.exists(GEM_EXECUTABLE)

    if not os.path.exists(BUNDLER_EXECUTABLE):
        subprocess.check_call([GEM_EXECUTABLE, 'install', 'bundler'])
    assert os.path.exists(BUNDLER_EXECUTABLE), BUNDLER_EXECUTABLE
