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
    source $BINDIR/activate

    PACKAGE=$(basename $d)

    python setup.py install
    pip install pytest coverage

    pushd $d
        python setup.py install
        rm -f .coverage
        if [ -e test_setup ]; then
            ./test_setup
        fi
        if [ -e manage.py ]; then
          PYTHONPATH=src python -m coverage run --rcfile=$COVERAGERC manage.py test
          pip install pytest-django
        else
          PYTHONPATH=src python -m coverage run  --rcfile=$COVERAGERC -m pytest tests
        fi
        python -m coverage report --fail-under=100
    popd
    deactivate

    rm -rf $VENV
done
