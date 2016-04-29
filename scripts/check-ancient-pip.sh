#!/usr/bin/env bash

set -e
set -x

PYTHON=$1

BROKEN_VIRTUALENV=$($PYTHON -c'import tempfile; print(tempfile.mkdtemp())')

trap "rm -rf $BROKEN_VIRTUALENV" EXIT

$PYTHON -m pip install virtualenv
$PYTHON -m virtualenv $BROKEN_VIRTUALENV
$BROKEN_VIRTUALENV/bin/pip install pytest
$BROKEN_VIRTUALENV/bin/python -m pip install --upgrade pip==1.0.0
$BROKEN_VIRTUALENV/bin/pip install .
$BROKEN_VIRTUALENV/bin/python -m pytest tests/cover/test_testdecorators.py
