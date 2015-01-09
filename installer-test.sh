set -e

TARGET=hypothesis-testing-chamber

rm -rf ./$TARGET
mkdir -p $TARGET
virtualenv $TARGET/venv
BINDIR=$(pwd)/$TARGET/venv/bin
PYTHON=$BINDIR/python
PIP=$BINDIR/pip

$PYTHON setup.py sdist 
$PIP install dist/*

cd $TARGET
$PYTHON -c 'from __future__ import print_function; from hypothesis import falsify; print(falsify(lambda x, y: x + y == y + x, str, str))'
