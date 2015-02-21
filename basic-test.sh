#!/bin/bash
set -e -o xtrace

pip install --upgrade hypothesis-extra/*/
python -m pytest --capture=no --strict tests/ hypothesis-extra/*/tests/
for f in hypothesis-extra/*/manage.py; do
    d=$(dirname $f)
    pushd $d
        python manage.py test
    popd
done
