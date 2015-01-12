set -e -o xtrace

VENV=hypothesis-testing-chamber

CURRENT_PYTHON=$(which python)

rm -rf ./dist
rm -rf ./$VENV
virtualenv $VENV  --python=$CURRENT_PYTHON
BINDIR=$(pwd)/$VENV/bin
PYTHON=$BINDIR/python

CURRENT_VERSION=$($CURRENT_PYTHON --version 2>&1)
VENV_VERSION=$($PYTHON --version 2>&1)

if [ "$CURRENT_VERSION" != "$VENV_VERSION" ]
then
  exit 1
fi

PIP=$BINDIR/pip

$PIP install pytest pytest-timeout

# Make sure hypothesis is not on the path
$PYTHON -c '
import sys
try:
    import hypothesis
    sys.exit(1)
except ImportError:
    pass
'

$PYTHON setup.py sdist 
$PIP install dist/*

$PYTHON -u -m pytest -v tests --maxfail=1
