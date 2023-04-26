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

export XDG_CACHE_HOME="$BUILD_RUNTIMES/.cache"
# export CARGO_HOME="$XDG_CACHE_HOME/.cargo"
# export RUSTUP_HOME="$XDG_CACHE_HOME/.rustup"

# Note: Deliberately ignoring BUILD_RUNTIMES configuration because we don't
# want this to go in cache, because it takes up a huge amount of space and
# slows everything down!
export VIRTUALENVS="${TMPDIR:-/tmp}/.hypothesis-runtimes/virtualenvs/"
# export RBENV_VERSION="2.5.1"
# export RBENV_ROOT="$BASE/.rbenv"
# export INSTALLED_RUBY_DIR="$RBENV_ROOT/versions/$RBENV_VERSION/"

# export GEM_HOME="$INSTALLED_RUBY_DIR"
# export GEM_PATH="$GEM_HOME"

# export PATH="$CARGO_HOME/bin:$INSTALLED_RUBY_DIR/bin:$HOME/.cargo/bin:$PATH"

pythonloc() {
    VERSION="$1"
    echo "$SNAKEPIT/$VERSION"
}
