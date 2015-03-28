#!/bin/bash

set -e
set -x

if [ ! -e "$HOME/.pyenv/bin/pyenv" ] ; then
  echo "pyenv does not exist"
  if [ -e "$HOME/.pyenv" ] ; then
    echo "Looks like a bad pyenv install. Deleting"
    rm -rf $HOME/.pyenv
  fi
fi

$(dirname $0)/pyenv-installer

export PATH="$HOME/.pyenv/bin:$HOME/.pyenv/shims:$PATH"


eval "$(pyenv init -)"
eval "$(pyenv virtualenv-init -)"

pyenv update || echo "Update failed to complete. Ignoring"


case "${TOXENV}" in
    py27)
        PYVERSION=2.7.8
        ;;
    py32)
        PYVERSION=3.2.6
        ;;
    py33)
        PYVERSION=3.3.6
        ;;
    py34)
        PYVERSION=3.4.2
        ;;
    pypy)
        PYVERSION=pypy-2.5.0
        ;;
    pypy3)
        PYVERSION=pypy3-2.4.0
        ;;
esac

if [ -z "$PYVERSION" ]; then
  PYVERSION=3.4.2
fi

pyenv install -s $PYVERSION
pyenv rehash
pyenv global $PYVERSION
pyenv local $PYVERSION

python --version
pip install --upgrade pip
pip install --upgrade virtualenv

if [ ! -d "$HOME/.venv" ] ; then
  rm -rf "$HOME/.venv"
  virtualenv "$HOME/.venv"
fi

source $HOME/.venv/bin/activate
pip install --upgrade tox
