#!/usr/bin/env bash

set -o errexit
set -o nounset

# This file is not really a script but is intended for sourcing from other
# scripts so that they can share a common set of paths conveniently.


HERE=$(dirname "$0")
export ROOT="$(git -C "$HERE" rev-parse --show-toplevel)"
export BUILD_RUNTIMES=${BUILD_RUNTIMES-$HOME/.cache/hypothesis-build-runtimes}
export BASE="$BUILD_RUNTIMES"
export PYENV="$BASE/pyenv"
export SNAKEPIT="$BASE/python-versions/"
export VIRTUALENVS="$BASE/virtualenvs/"

pythonloc() {
    VERSION="$1"
    echo "$SNAKEPIT/$VERSION"
}
