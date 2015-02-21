#!/bin/bash
set -e -o xtrace

TOP_LEVEL=$(cd $(dirname $0); pwd)
COVERAGERC=$TOP_LEVEL/.coveragerc

for d in hypothesis-extra/hypothesis-*; do
    VENV=$(python -c 'import tempfile; print(tempfile.mkdtemp())')

    CURRENT_PYTHON=$(which python)

    rm -rf ./dist
    virtualenv $VENV  --python=$CURRENT_PYTHON
    BINDIR=$VENV/bin
    PYTHON=$BINDIR/python
    PIP=$BINDIR/pip

    PACKAGE=$(basename $d)

    $PYTHON setup.py install
    $PIP install pytest coverage

    pushd $d
        $PIP install -r requirements.txt
        $PYTHON setup.py develop
        rm -f .coverage
        if [ -e manage.py ]; then
          PYTHONPATH=src $PYTHON -m coverage run --rcfile=$COVERAGERC manage.py test
          pip install pytest-django
        else
          PYTHONPATH=src $PYTHON -m coverage run  --rcfile=$COVERAGERC -m pytest tests
        fi
        $PYTHON -m coverage report --fail-under=100
    popd

    rm -rf $VENV
done
