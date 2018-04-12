#!/usr/bin/env bash

# This script is here to bootstrap the Hypothesis build process into a working
# version of Python, then hand over to the actual Hypothesis build runner (which
# is written in Python instead of bash).

set -x
set -o errexit
set -o nounset

ROOT="$(git -C "$(dirname "$0")" rev-parse --show-toplevel)"

export HYPOTHESIS_ROOT="$ROOT"

SCRIPTS="$ROOT/tooling/scripts"

# shellcheck source=tooling/scripts/common.sh
source "$SCRIPTS/common.sh"

"$SCRIPTS/ensure-python.sh" 3.6.5

PYTHON=$(pythonloc 3.6.5)/bin/python

TOOL_REQUIREMENTS="$ROOT/requirements/tools.txt"

TOOL_HASH=$("$PYTHON" "$SCRIPTS/tool-hash.py" < "$TOOL_REQUIREMENTS")

TOOL_VIRTUALENV="$VIRTUALENVS/build-$TOOL_HASH"
TOOL_PYTHON="$TOOL_VIRTUALENV/bin/python"

if [ ! -e "$TOOL_PYTHON" ] ; then
    rm -rf "$TOOL_VIRTUALENV"
    "$PYTHON" -m pip install --upgrade virtualenv
	"$PYTHON" -m virtualenv "$TOOL_VIRTUALENV"
	"$TOOL_PYTHON" -m pip install -r requirements/tools.txt
	"$TOOL_PYTHON" -m pip install -e tooling
fi

"$TOOL_PYTHON" -m hypothesistooling "$@"
