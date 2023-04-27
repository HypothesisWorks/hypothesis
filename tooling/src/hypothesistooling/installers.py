# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

"""Module for obtaining various versions of Python.

Currently this is a thin shim around pyenv, but it would be nice to have
this work on Windows as well by using Anaconda (as our build already
does).
"""

import os
import shutil
import subprocess

from hypothesistooling import scripts
from hypothesistooling.junkdrawer import once

HOME = os.environ["HOME"]


def __python_executable(version):
    return os.path.join(scripts.SNAKEPIT, version, "bin", "python")


def python_executable(version):
    ensure_python(version)
    return __python_executable(version)


PYTHONS = set()


def ensure_python(version):
    if version in PYTHONS:
        return
    scripts.run_script("ensure-python.sh", version)
    target = __python_executable(version)
    assert os.path.exists(target), target
    PYTHONS.add(version)


STACK = os.path.join(HOME, ".local", "bin", "stack")
GHC = os.path.join(HOME, ".local", "bin", "ghc")
SHELLCHECK = shutil.which("shellcheck") or os.path.join(
    HOME, ".local", "bin", "shellcheck"
)


def ensure_stack():
    if os.path.exists(STACK):
        return
    subprocess.check_call("mkdir -p ~/.local/bin", shell=True)
    subprocess.check_call(
        "curl -L https://www.stackage.org/stack/linux-x86_64 "
        "| tar xz --wildcards --strip-components=1 -C $HOME"
        "/.local/bin '*/stack'",
        shell=True,
    )


@once
def update_stack():
    ensure_stack()
    subprocess.check_call([STACK, "update"])


@once
def ensure_ghc():
    if os.path.exists(GHC):
        return
    update_stack()
    subprocess.check_call([STACK, "setup"])


@once
def ensure_shellcheck():
    if os.path.exists(SHELLCHECK):
        return
    update_stack()
    ensure_ghc()
    subprocess.check_call([STACK, "install", "ShellCheck"])


@once
def ensure_rustup():
    scripts.run_script("ensure-rustup.sh")


# RUBY_BUILD = os.path.join(scripts.RBENV_ROOT, "plugins", "ruby-build")

# RUBY_BIN_DIR = os.path.join(scripts.INSTALLED_RUBY_DIR, "bin")

# BUNDLER_EXECUTABLE = os.path.join(RUBY_BIN_DIR, "bundle")
# GEM_EXECUTABLE = os.path.join(RUBY_BIN_DIR, "gem")

# RBENV_COMMAND = os.path.join(scripts.RBENV_ROOT, "bin", "rbenv")


# @once
# def ensure_ruby():
#     if not os.path.exists(scripts.RBENV_ROOT):
#         git("clone", "https://github.com/rbenv/rbenv.git", scripts.RBENV_ROOT)
#
#     if not os.path.exists(RUBY_BUILD):
#         git("clone", "https://github.com/rbenv/ruby-build.git", RUBY_BUILD)
#
#     if not os.path.exists(
#         os.path.join(scripts.RBENV_ROOT, "versions", scripts.RBENV_VERSION)
#     ):
#         subprocess.check_call([RBENV_COMMAND, "install", scripts.RBENV_VERSION])
#
#     subprocess.check_call([GEM_EXECUTABLE, "update", "--system"])
#
#     if not (
#         os.path.exists(BUNDLER_EXECUTABLE)
#         and subprocess.call([BUNDLER_EXECUTABLE, "version"]) == 0
#     ):
#         subprocess.check_call([GEM_EXECUTABLE, "install", "bundler"])
#
#     assert os.path.exists(BUNDLER_EXECUTABLE)
