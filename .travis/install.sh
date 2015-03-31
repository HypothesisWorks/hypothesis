#!/bin/bash

# Special license: Take literally anything you want out of this file. I don't
# care. Consider it WTFPL licensed if you like.
# Basically there's a lot of suffering encoded here that I don't want you to
# have to go through and you should feel free to use this to avoid some of
# that suffering in advance.

set -e
set -x

# This is to guard against multiple builds in parallel. The various installers will tend
# to stomp all over eachother if you do this and they haven't previously successfully
# succeeded. We use a lock file to block progress so only one install runs at a time.
# This script should be pretty fast once files are cached, so the lost of concurrency
# is not a major problem.
# This should be using the lockfile command, but that's not available on the
# containerized travis and we can't install it without sudo.
# Is is unclear if this is actually useful. I was seeing behaviour that suggested
# concurrent runs of the installer, but I can't seem to find any evidence of this lock
# ever not being acquired. 
LOCKFILE="$HOME/.install-lockfile"
while true; do
  if mkdir $LOCKFILE 2>/dev/null; then
    echo "Successfully acquired lock"
    break
  else
    echo "Failed to acquire lock. Waiting our turn"
  fi

  sleep $[ ( $RANDOM % 10)  + 1 ].$[ ( $RANDOM % 100) ]s

  if (( $(date '+%s') > 300 + $(stat --format=%X $LOCKFILE) )); then
    echo "We've waited long enough"
    rm -rf $LOCKFILE
  fi
done
trap "rm -rf $LOCKFILE" EXIT


# Somehow we occasionally get broken installs of pyenv, and pyenv-installer
# is not good at detecting and cleaning up from those. We use the existence
# of a pyenv executable as a proxy for whether pyenv is actually installed
# correctly, but only because that's the only error I've seen so far.
if [ ! -e "$HOME/.pyenv/bin/pyenv" ] ; then
  echo "pyenv does not exist"
  if [ -e "$HOME/.pyenv" ] ; then
    echo "Looks like a bad pyenv install. Deleting"
    rm -rf $HOME/.pyenv
  fi
fi

# Run the pyenv-installer script we've bundled.
# This is basically vendored from >https://github.com/yyuu/pyenv-installer
$(dirname $0)/pyenv-installer

# Now that pyenv is installed, run the commands it gives us to actually
# activate it.
export PATH="$HOME/.pyenv/bin:$PATH"
eval "$(pyenv init -)"
eval "$(pyenv virtualenv-init -)"


# pyenv update makes a lot of requests to github, which is not entirely
# reliable. As long as we got a working pyenv in the first place (above) we
# don't want to fail the build if pyenv can't update. Given that .pyenv is
# cached anyway, the version we have should probably be quite recent.
pyenv update || echo "Update failed to complete. Ignoring"

# TOXENV sets the version of python we need for running tox itself. Make sure
# we have that installed.
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

# Default to 3.4.2, mostly for things like lint.
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

# We might have got a bad version of the virtualenv. We check that and recover
# in a similar way to how we do for pyenv.
if [ ! -e "$HOME/.venv/bin/activate" ] ; then
  rm -rf "$HOME/.venv"
  virtualenv "$HOME/.venv"
fi

source $HOME/.venv/bin/activate
pip install --upgrade tox
