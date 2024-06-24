#!/usr/bin/env bash

if [ -n "${CI:-}" ] ; then echo "::group::Ensure Python" ; fi

set -o errexit
set -o nounset
set -x

HERE="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# shellcheck source=tooling/scripts/common.sh
source "$HERE/common.sh"

# This is to guard against multiple builds in parallel. The various installers will tend
# to stomp all over each other if you do this and they haven't previously successfully
# succeeded. We use a lock file to block progress so only one install runs at a time.
# This script should be pretty fast once files are cached, so the loss of concurrency
# is not a major problem.
# This should be using the lockfile command, but that's not available on the
# containerized travis and we can't install it without sudo.
# It is unclear if this is actually useful. I was seeing behaviour that suggested
# concurrent runs of the installer, but I can't seem to find any evidence of this lock
# ever not being acquired.

VERSION="$1"
TARGET=$(pythonloc "$VERSION")

if [ ! -e "$TARGET/bin/python" ] ; then
    mkdir -p "$BASE"

    LOCKFILE="$BASE/.install-lockfile"
    while true; do
      if mkdir "$LOCKFILE" 2>/dev/null; then
        echo "Successfully acquired installer."
        break
      else
        echo "Failed to acquire lock. Is another installer running? Waiting a bit."
      fi

      sleep $(( ( RANDOM % 10 ) + 1 )).$(( RANDOM % 100 ))s

      if (( $(date '+%s') > 300 + $(stat --format=%X "$LOCKFILE") )); then
        echo "We've waited long enough"
        rm -rf "$LOCKFILE"
      fi
    done
    trap 'rm -rf $LOCKFILE' EXIT


    if [ ! -d "$PYENV/.git" ]; then
      rm -rf "$PYENV"
      git clone https://github.com/yyuu/pyenv.git "$PYENV"
    else
      back=$PWD
      cd "$PYENV"
      git fetch || echo "Update failed to complete. Ignoring"
      git reset --hard origin/master
      cd "$back"
    fi

    for _ in $(seq 5); do
        if "$BASE/pyenv/plugins/python-build/bin/python-build" "$VERSION" "$TARGET" ; then
            exit 0
        fi
        echo "Command failed. For a possible solution, visit"
        echo "https://github.com/pyenv/pyenv/wiki#suggested-build-environment."
        echo "Retrying..."
        sleep $(( ( RANDOM % 10 )  + 1 )).$(( RANDOM % 100 ))s
    done
fi

if [ -n "${CI:-}" ] ; then echo "::endgroup::" ; fi
