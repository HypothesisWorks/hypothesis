set -e -o xtrace

for d in hypothesis-extra/*; do
    VENV=$(mktemp -d)

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

    pushd $d
        $PYTHON setup.py install
        $PIP install pytest
        $PYTHON -m pytest tests
    popd
done
