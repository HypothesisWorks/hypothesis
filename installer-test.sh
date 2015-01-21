set -e -o xtrace

VENV=$(mktemp -d)

CURRENT_PYTHON=$(which python)

rm -rf ./dist
virtualenv $VENV  --python=$CURRENT_PYTHON
BINDIR=$VENV/bin
PYTHON=$BINDIR/python

CURRENT_VERSION=$($CURRENT_PYTHON --version 2>&1)
VENV_VERSION=$($PYTHON --version 2>&1)

if [ "$CURRENT_VERSION" != "$VENV_VERSION" ]
then
  exit 1
fi

PIP=$BINDIR/pip

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

# Make sure pytest is not on the path
$PYTHON -c '
import sys
try:
    import pytest 
    sys.exit(1)
except ImportError:
    pass
'

# Make sure we can load and falsify something without pytest
$PYTHON -c '
import hypothesis
print(hypothesis.falsify(lambda x, y: x + y == y + x, str, str))
'



$PIP install pytest pytest-timeout

$PYTHON -u -m pytest -v tests --maxfail=1
