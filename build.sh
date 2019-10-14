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

if [ -n "${PIPELINE_WORKSPACE-}" ] ; then
    # We're on Azure Pipelines and already set up a suitable Python
    PYTHON=$(command -v python)
else
    # Otherwise, we install it from scratch
    "$SCRIPTS/ensure-python.sh" 3.6.8
    PYTHON=$(pythonloc 3.6.8)/bin/python
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
  "$TOOL_PYTHON" -m pip install --no-warn-script-location -r requirements/tools.txt
fi

"$TOOL_PYTHON" -m hypothesistooling "$@"
