#!/usr/bin/env bash

if [ -n "${CI:-}" ] ; then echo "::group::Ensure Python" ; fi

set -o errexit
set -o nounset
set -x

HERE="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# shellcheck source=tooling/scripts/common.sh
source "$HERE/common.sh"

VERSION="$1"
TARGET=$(pythonloc "$VERSION")

if [ -e "$TARGET/bin/python" ] ; then
    if [ -n "${CI:-}" ] ; then echo "::endgroup::" ; fi
    exit 0
fi

mkdir -p "$BASE"

# Serialise installs so concurrent builds don't stomp on each other. `uv`
# itself is pretty resilient, but translating a version into a uv request
# and then linking things into SNAKEPIT isn't, and we've historically had
# problems here. Keep the lockfile approach as a simple safety net.
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

"$HERE/ensure-uv.sh"
if ! command -v uv >/dev/null 2>&1 ; then
    export PATH="$HOME/.local/bin:$PATH"
fi

# Translate our version strings into uv's request format.
# - 3.14.4 stays as 3.14.4
# - 3.13t / 3.13t-dev -> 3.13+freethreaded
# - 3.13.5t -> 3.13.5+freethreaded
# - pypy3.10-7.3.19 -> pypy@3.10 (uv tracks pypy by python version)
translate_version() {
    local v="$1"
    if [[ "$v" =~ ^pypy([0-9]+)\.([0-9]+) ]]; then
        echo "pypy@${BASH_REMATCH[1]}.${BASH_REMATCH[2]}"
    elif [[ "$v" =~ ^([0-9]+\.[0-9]+(\.[0-9]+)?)t(-dev)?$ ]]; then
        echo "${BASH_REMATCH[1]}+freethreaded"
    else
        echo "$v"
    fi
}

REQUEST=$(translate_version "$VERSION")

mkdir -p "$SNAKEPIT" "$UV_PYTHON_INSTALL_DIR"

uv python install "$REQUEST"
PYTHON_BIN=$(uv python find --managed-python "$REQUEST")
INSTALL_ROOT=$(dirname "$(dirname "$PYTHON_BIN")")

# uv installs the interpreter as e.g. python3.14; our callers expect a plain
# `python` alongside it, so create one in the managed directory if absent.
if [ ! -e "$INSTALL_ROOT/bin/python" ] ; then
    ln -s "$(basename "$PYTHON_BIN")" "$INSTALL_ROOT/bin/python"
fi

# Present the install at its legacy path ($SNAKEPIT/$VERSION) so the rest of
# the build system can keep using pythonloc() unchanged.
rm -rf "$TARGET"
ln -s "$INSTALL_ROOT" "$TARGET"

if [ -n "${CI:-}" ] ; then echo "::endgroup::" ; fi
