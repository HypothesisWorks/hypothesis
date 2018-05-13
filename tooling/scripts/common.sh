#!/usr/bin/env bash

# This file is not really a script but is intended for sourcing from other
# scripts so that they can share a common set of paths conveniently.

set -o errexit
set -o nounset

HERE="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
ROOT="$(git -C "$HERE" rev-parse --show-toplevel)"

export ROOT
export BUILD_RUNTIMES=${BUILD_RUNTIMES:-$HOME/.cache/hypothesis-build-runtimes}
export BASE="$BUILD_RUNTIMES"
export PYENV="$BASE/pyenv"
export SNAKEPIT="$BASE/python-versions/"
export VIRTUALENVS="$BASE/virtualenvs/"
export RBENV_VERSION="2.5.1"
export RBENV_ROOT="$BASE/.rbenv"
export INSTALLED_RUBY_DIR="$RBENV_ROOT/versions/$RBENV_VERSION/"

export GEM_HOME="$INSTALLED_RUBY_DIR"
export GEM_PATH="$GEM_HOME"

export PATH="$INSTALLED_RUBY_DIR/bin:$HOME/.cargo/bin:$PATH"

pythonloc() {
    VERSION="$1"
    echo "$SNAKEPIT/$VERSION"
}
