#!/bin/bash

set -e
set -x

export PATH="$HOME/snakepit:$HOME/.pyenv/bin:$PATH"
eval "$(pyenv init -)"
pyenv local 3.4.3
tox -- $TOX_FLAGS
