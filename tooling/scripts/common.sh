#!/usr/bin/env bash

# This file is not really a script but is intended for sourcing from other
# scripts so that they can share a common set of paths and functions.

set -o errexit
set -o nounset
set -o pipefail

HERE="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
ROOT="$(git -C "$HERE" rev-parse --show-toplevel)"

export ROOT
export BUILD_RUNTIMES=${BUILD_RUNTIMES:-$HOME/.cache/hypothesis-build-runtimes}
export BASE="$BUILD_RUNTIMES"
export SNAKEPIT="$BASE/python-versions/"
export UV_PYTHON_INSTALL_DIR="$SNAKEPIT/.uv-managed"

export XDG_CACHE_HOME="$BUILD_RUNTIMES/.cache"

export RUSTUP_HOME="$BUILD_RUNTIMES/rustup"
export CARGO_HOME="$BUILD_RUNTIMES/cargo"
export UV_HOME="$BUILD_RUNTIMES/uv"  # Directory directly containing `uv` binary

export PATH="$CARGO_HOME/bin:$UV_HOME:$PATH"

# Note: Deliberately ignoring BUILD_RUNTIMES configuration because we don't
# want this to go in cache, because it takes up a huge amount of space and
# slows everything down!
export VIRTUALENVS="${TMPDIR:-/tmp}/.hypothesis-runtimes/virtualenvs/"

pythonloc() {
    VERSION="$1"
    echo "$SNAKEPIT/$VERSION"
}

ensure-uv() {
    # Ensure `uv` is installed at $UV_PATH and $PATH resolves to this version.

    local expected_path
    if ! expected_path=$(readlink -f "$UV_HOME/uv"); then
        install-uv
        expected_path=$(readlink -f "$UV_HOME/uv")
    fi

    local actual_path
    if ! actual_path=$(type -P uv); then
        echo "uv installed at $expected_path, but not found on PATH $PATH" 1>&2
        return 1
    fi

    if [[ "$expected_path" != "$actual_path" ]]; then
        echo "uv installed at $expected_path, but resolved on PATH $PATH to $actual_path" 1>&2
        return 1
    fi

    return
}

install-uv() {
    # Install `uv` into $UV_HOME, using the installer from astral.sh.

    if [ -n "${CI:-}" ] ; then echo "::group::Install uv" ; fi

    # UV_INSTALL_DIR: exact directory to install uv in, bin is not appended.
    # UV_NO_MODIFY_PATH: don't modify $PATH, including later runs of `uv self update`.
    # https://docs.astral.sh/uv/reference/installer/
    curl -LsSf https://astral.sh/uv/install.sh | UV_INSTALL_DIR="$UV_HOME" UV_NO_MODIFY_PATH="1" sh

    if [ -n "${CI:-}" ] ; then echo "::endgroup::" ; fi
}
