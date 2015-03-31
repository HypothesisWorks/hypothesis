#!/bin/bash

set -e
set -x

ulimit -m 2000000 -v 2000000

export PATH="$HOME/.pyenv/bin:$HOME/.pyenv/shims:$PATH"
eval "$(pyenv init -)"
source ~/.venv/bin/activate
tox -- $TOX_FLAGS
