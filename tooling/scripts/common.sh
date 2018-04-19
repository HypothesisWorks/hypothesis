#!/usr/bin/env bash

# This file is not really a script but is intended for sourcing from other
# scripts so that they can share a common set of paths conveniently.

set -o errexit
set -o nounset

HERE="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
ROOT="$(git -C "$HERE" rev-parse --show-toplevel)"

export ROOT
export BUILD_RUNTIMES=${BUILD_RUNTIMES-$HOME/.cache/hypothesis-build-runtimes}
export BASE="$BUILD_RUNTIMES"
export PYENV="$BASE/pyenv"
export SNAKEPIT="$BASE/python-versions/"
export VIRTUALENVS="$BASE/virtualenvs/"

pythonloc() {
    VERSION="$1"
    echo "$SNAKEPIT/$VERSION"
}
