set -e

VENV=hypothesis-testing-chamber

rm -rf ./dist
rm -rf ./$VENV
virtualenv $VENV
BINDIR=$(pwd)/$VENV/bin
PYTHON=$BINDIR/python
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
