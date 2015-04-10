#!/bin/bash

set -e
set -x

ulimit -m 2000000 -v 2000000

# we have that installed.
case "${TOXENV}" in
    py27)
        export PYVERSION=2.7.8
        ;;
    py32)
        export PYVERSION=3.2.6
        ;;
    py33)
        export PYVERSION=3.3.6
        ;;
    py34)
        export PYVERSION=3.4.2
        ;;
    pypy)
        export PYVERSION=pypy-2.5.0
        ;;
    pypy3)
        export PYVERSION=pypy3-2.4.0
        ;;
esac

# Default to 3.4.2, mostly for things like lint.
if [ -z "$PYVERSION" ]; then
  PYVERSION=3.4.2
fi

export PATH="$HOME/.pyenv/bin:$PATH"
eval "$(pyenv init -)"
pyenv local $PYVERSION

source ~/.venv/bin/activate
tox -- $TOX_FLAGS
