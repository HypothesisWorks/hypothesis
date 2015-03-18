#!/bin/bash
set -e -o xtrace

python setup.py develop
pip install --upgrade hypothesis-extra/hypothesis-datetime/
#python -m pytest --capture=no --strict tests/
python -m pytest --capture=no --strict hypothesis-extra/hypothesis-datetime/tests/
for f in hypothesis-extra/*/manage.py; do
    d=$(dirname $f)
    pushd $d
        python manage.py test
    popd
done
