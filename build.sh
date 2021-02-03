#!/usr/bin/env bash

# This script is here to bootstrap the Hypothesis build process into a working
# version of Python, then hand over to the actual Hypothesis build runner (which
# is written in Python instead of bash).

set -o xtrace
set -o errexit
set -o nounset

ROOT="$(git -C "$(dirname "$0")" rev-parse --show-toplevel)"

export HYPOTHESIS_ROOT="$ROOT"

SCRIPTS="$ROOT/tooling/scripts"

# shellcheck source=tooling/scripts/common.sh
source "$SCRIPTS/common.sh"

if [ -n "${GITHUB_ACTIONS-}" ] ; then
    # We're on GitHub Actions and already set up a suitable Python
    PYTHON=$(command -v python)
else
    # Otherwise, we install it from scratch
    # NOTE: keep this version in sync with PYMAIN in tooling
    "$SCRIPTS/ensure-python.sh" 3.8.7
    PYTHON=$(pythonloc 3.8.7)/bin/python
fi

TOOL_REQUIREMENTS="$ROOT/requirements/tools.txt"

TOOL_HASH=$("$PYTHON" "$SCRIPTS/tool-hash.py" < "$TOOL_REQUIREMENTS")

TOOL_VIRTUALENV="$VIRTUALENVS/build-$TOOL_HASH"
TOOL_PYTHON="$TOOL_VIRTUALENV/bin/python"

export PYTHONPATH="$ROOT/tooling/src"

if ! "$TOOL_PYTHON" -m hypothesistooling check-installed ; then
  rm -rf "$TOOL_VIRTUALENV"
  "$PYTHON" -m pip install --upgrade pip
  "$PYTHON" -m pip install --upgrade virtualenv
  "$PYTHON" -m virtualenv "$TOOL_VIRTUALENV"
  # We install from the pinned tool dependencies, but if that fails AND we're running
  # the whole-repo tests to update pinned dependencies, install from unpinned.
  # (because pyup will cheerfully "upgrade" to an incompatible set of pins)
  # TODO: remove this logic once we have a better automatic update system.
  {
    "$TOOL_PYTHON" -m pip install --no-warn-script-location -r requirements/tools.txt
  } || {
      if [ "$TASK" == "check-whole-repo-tests" ]; then
        "$TOOL_PYTHON" -m pip install --no-warn-script-location -r requirements/tools.in
      else
        exit 1
      fi
  }
fi

"$TOOL_PYTHON" -m hypothesistooling "$@"
