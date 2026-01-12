#!/usr/bin/env bash

# This script is here to bootstrap the Hypothesis build process into a working
# version of Python, then hand over to the actual Hypothesis build runner (which
# is written in Python instead of bash).

if [ -n "${CI:-}" ] ; then echo "::group::Build setup" ; fi

set -o xtrace
set -o errexit
set -o nounset

ROOT="$(git -C "$(dirname "$0")" rev-parse --show-toplevel)"

export HYPOTHESIS_ROOT="$ROOT"

SCRIPTS="$ROOT/tooling/scripts"

# shellcheck source=tooling/scripts/common.sh
source "$SCRIPTS/common.sh"

if [ -n "${GITHUB_ACTIONS-}" ] || [ -n "${CODESPACES-}" ] || [ -n "${CLAUDECODE-}" ] ; then
    # We're on GitHub Actions, Codespaces, or Claude Code and already have a suitable Python
    PYTHON=$(command -v python3 || command -v python)
else
    # Otherwise, we install it from scratch
    # NOTE: tooling keeps this version in sync with ci_version in tooling
    "$SCRIPTS/ensure-python.sh" 3.10.19
    PYTHON=$(pythonloc 3.10.19)/bin/python
fi

TOOL_REQUIREMENTS="$ROOT/requirements/tools.txt"

# append PYTHON_VERSION to bust caches when we upgrade versions
TOOL_HASH=$( (cat "$TOOL_REQUIREMENTS" && echo "$PYTHON_VERSION") | "$PYTHON" "$SCRIPTS/tool-hash.py")

TOOL_VIRTUALENV="$VIRTUALENVS/build-$TOOL_HASH"
TOOL_PYTHON="$TOOL_VIRTUALENV/bin/python"

export PYTHONPATH="$ROOT/tooling/src"

if ! "$TOOL_PYTHON" -m hypothesistooling check-installed ; then
  rm -rf "$TOOL_VIRTUALENV"
  if [ -n "${CLAUDECODE-}" ] ; then
    # Claude Code: use venv (available) and skip pip upgrades (debian-managed)
    "$PYTHON" -m venv "$TOOL_VIRTUALENV"
  else
    "$PYTHON" -m pip install --upgrade pip
    "$PYTHON" -m pip install --upgrade virtualenv
    "$PYTHON" -m virtualenv "$TOOL_VIRTUALENV"
  fi
  "$TOOL_PYTHON" -m pip install --no-warn-script-location -r requirements/tools.txt
fi

if [ -n "${CI:-}" ] ; then echo "::endgroup::" ; fi

"$TOOL_PYTHON" -m hypothesistooling "$@"
