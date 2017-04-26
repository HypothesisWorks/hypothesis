#!/usr/bin/env bash

set -e
set -x

PYTHON=$1

BROKEN_VIRTUALENV=$($PYTHON -c'import tempfile; print(tempfile.mkdtemp())')

trap 'rm -rf $BROKEN_VIRTUALENV' EXIT

rm -rf tmp-dist-dir

$PYTHON setup.py sdist --dist-dir=tmp-dist-dir

$PYTHON -m pip install virtualenv
$PYTHON -m virtualenv "$BROKEN_VIRTUALENV"
"$BROKEN_VIRTUALENV"/bin/pip install -rrequirements/test.txt

# These are versions from debian stable as of 2017-04-21
# See https://packages.debian.org/stable/python/
"$BROKEN_VIRTUALENV"/bin/python -m pip install --upgrade pip==1.5.6
"$BROKEN_VIRTUALENV"/bin/pip install --upgrade setuptools==5.5.1
"$BROKEN_VIRTUALENV"/bin/pip install tmp-dist-dir/*
"$BROKEN_VIRTUALENV"/bin/python -m pytest tests/cover/test_testdecorators.py
