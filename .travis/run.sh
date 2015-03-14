#!/bin/bash

set -e
set -x

ulimit -m 2000000 -v 2000000

if [[ "$(uname -s)" == "Darwin" ]]; then
    eval "$(pyenv init -)"
fi
source ~/.venv/bin/activate
tox -- $TOX_FLAGS
