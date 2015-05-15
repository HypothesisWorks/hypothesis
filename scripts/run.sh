#!/bin/bash

set -e
set -x

if [ "$TOXENV" != "pypy" ]; then
    if [ "$TOXENV" != "pypy3" ];  then
        ulimit -m 2000000 -v 2000000
    fi
fi

export PATH="$HOME/snakepit:$HOME/.pyenv/bin:$PATH"
eval "$(pyenv init -)"
pyenv local 3.4.3
tox -- $TOX_FLAGS
