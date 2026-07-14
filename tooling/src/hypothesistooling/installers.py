# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

"""Module for obtaining various language toolchains."""

import os
import shutil
import subprocess

from hypothesistooling import scripts

HOME = os.environ["HOME"]
INSTALLED_PYTHONS = set()
INSTALLED_RUSTS = set()

CARGO_HOME = os.environ.get("CARGO_HOME") or os.path.join(HOME, ".cargo")
RUSTUP = os.path.join(CARGO_HOME, "bin", "rustup")

STACK = os.path.join(HOME, ".local", "bin", "stack")
SHELLCHECK = shutil.which("shellcheck") or os.path.join(
    HOME, ".local", "bin", "shellcheck"
)


def once(fn):
    def accept():
        if accept.has_been_called:
            return
        fn()
        accept.has_been_called = True

    accept.has_been_called = False
    accept.__name__ = fn.__name__
    return accept


def __python_executable(version):
    return os.path.join(scripts.SNAKEPIT, version, "bin", "python")


def python_executable(version):
    ensure_python(version)
    return __python_executable(version)


def ensure_python(version):
    if version in INSTALLED_PYTHONS:
        return
    scripts.run_script("ensure-python.sh", version)
    target = __python_executable(version)
    assert os.path.exists(target), target
    INSTALLED_PYTHONS.add(version)


@once
def ensure_rustup():
    if os.path.exists(RUSTUP):
        return
    subprocess.check_call(
        "curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs "
        "| sh -s -- -y --no-modify-path --default-toolchain none",
        shell=True,
        # don't abort just because a system rustup exists on PATH
        env={**os.environ, "RUSTUP_INIT_SKIP_PATH_CHECK": "yes"},
    )


def ensure_rustc(version, *, components=(), targets=()):
    key = (version, *components, *targets)
    if key in INSTALLED_RUSTS:
        return
    ensure_rustup()
    subprocess.check_call(
        [RUSTUP, "toolchain", "install", version, "--profile", "minimal"]
        + [arg for component in components for arg in ("--component", component)]
    )
    if targets:
        subprocess.check_call(
            [RUSTUP, "target", "add", *targets, "--toolchain", version]
        )
    INSTALLED_RUSTS.add(key)


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
