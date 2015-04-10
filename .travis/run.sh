#!/bin/bash

set -e
set -x

ulimit -m 2000000 -v 2000000

export PATH="$HOME/snakepit:$HOME/.pyenv/bin:$PATH"
eval "$(pyenv init -)"
pyenv local 3.4.3
tox -- $TOX_FLAGS
