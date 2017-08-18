#!/usr/bin/env bash

set -e
set -u
set -x

SPHINX_BUILD=$1
PYTHON=$2

HERE="$(dirname $0)"

cd "$HERE"/..

trap "git checkout docs/changes.rst src/hypothesis/version.py" EXIT

$PYTHON scripts/update-changelog-for-docs.py

export PYTHONPATH=src 

$SPHINX_BUILD -W -b html -d docs/_build/doctrees docs docs/_build/html
