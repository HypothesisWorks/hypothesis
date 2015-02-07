#!/bin/bash

set -e
set -x

if [[ "$(uname -s)" == "Darwin" ]]; then
    eval "$(pyenv init -)"
fi
source ~/.venv/bin/activate
tox -- $TOX_FLAGS
