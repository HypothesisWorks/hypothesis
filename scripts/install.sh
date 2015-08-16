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


# pyenv update makes a lot of requests to github, which is not entirely
# reliable. As long as we got a working pyenv in the first place (above) we
# don't want to fail the build if pyenv can't update. Given that .pyenv is
# cached anyway, the version we have should probably be quite recent.
pyenv update || echo "Update failed to complete. Ignoring"

SNAKEPIT=$HOME/snakepit

rm -rf $SNAKEPIT
mkdir $SNAKEPIT

PYENVS=$HOME/.pyenv/versions

pyenv install -s 3.4.3
ln -s $PYENVS/3.4.3/bin/python $SNAKEPIT/python3.4
echo 3.4.3 > $HOME/.python-version
pyenv global 3.4.3
pyenv local 3.4.3

case "${TOXENV}" in
    py26|examples2)
        pyenv install -s 2.6.9
        ln -s $PYENVS/2.6.9/bin/python $SNAKEPIT/python2.6
        ;;
    py27|examples2)
        pyenv install -s 2.7.9
        ln -s $PYENVS/2.7.9/bin/python $SNAKEPIT/python2.7
        ;;
    py32)
        pyenv install -s 3.2.6
        ln -s $PYENVS/3.2.6/bin/python $SNAKEPIT/python3.2
        ;;
    py33)
        pyenv install -s 3.3.6
        ln -s $PYENVS/3.3.6/bin/python $SNAKEPIT/python3.3
        ;;
    pypy)
        pyenv install -s pypy-2.6.0
        ln -s $PYENVS/pypy-2.6.0/bin/pypy $SNAKEPIT/pypy
        ;;
    pypy3)
        pyenv install -s pypy3-2.4.0
        ln -s $PYENVS/pypy3-2.4.0/bin/pypy $SNAKEPIT/pypy3
        ;;
    pypy3-nojit)
        pyenv install -s pypy3-2.4.0
        ln -s $PYENVS/pypy3-2.4.0/bin/pypy $SNAKEPIT/pypy3
        ;;
esac

pip install --upgrade tox pip wheel
