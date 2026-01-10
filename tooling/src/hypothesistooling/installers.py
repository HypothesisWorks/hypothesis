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
SHELLCHECK = shutil.which("shellcheck") or os.path.join(
    HOME, ".local", "bin", "shellcheck"
)


def ensure_stack():
    if os.path.exists(STACK):
        return
    subprocess.check_call("mkdir -p ~/.local/bin", shell=True)
    # if you're on macos, this will error with "--wildcards is not supported"
    # or similar. You should put shellcheck on your PATH with your package
    # manager of choice; eg `brew install shellcheck`.
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
def ensure_shellcheck():
    if os.path.exists(SHELLCHECK):
        return
    update_stack()
    subprocess.check_call([STACK, "install", "ShellCheck"])
