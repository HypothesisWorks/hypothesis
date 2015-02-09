#!/bin/bash
set -e -o xtrace

for d in hypothesis-extra/*; do
    VENV=$(python -c 'import tempfile; print(tempfile.mkdtemp())')

    CURRENT_PYTHON=$(which python)

    rm -rf ./dist
    virtualenv $VENV  --python=$CURRENT_PYTHON
    BINDIR=$VENV/bin
    PYTHON=$BINDIR/python
    PIP=$BINDIR/pip

    CURRENT_VERSION=$($CURRENT_PYTHON --version 2>&1)
    VENV_VERSION=$($PYTHON --version 2>&1)

    if [ "$CURRENT_VERSION" != "$VENV_VERSION" ]
    then
      exit 1
    fi

    $PYTHON setup.py install
    $PIP install pytest coverage

    pushd $d
        $PIP install -r requirements.txt
        $PYTHON setup.py develop
        PYTHONPATH=src $PYTHON -m coverage run --include="src/**/*.py" -m pytest tests
        $PYTHON -m coverage report --fail-under=100
        $PYTHON setup.py install
        $PYTHON -m pytest tests
    popd

    rm -rf $VENV
done
