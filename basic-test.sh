#!/bin/bash
set -e -o xtrace

if [ "$(python -c 'import platform; print(platform.python_implementation())')" = "PyPy" ]; then
    pip install git+https://bitbucket.org/pypy/numpy.git
fi

pip install --upgrade hypothesis-extra/hypothesis-datetime/
pip install --upgrade hypothesis-extra/hypothesis-fakefactory/
pip install --upgrade hypothesis-extra/hypothesis-pytest/
pip install --upgrade hypothesis-extra/hypothesis-django/
pip install --upgrade hypothesis-extra/hypothesis-numpy/
python -m pytest --capture=no --strict tests/ --durations=20
python -m pytest --capture=no --strict hypothesis-extra/*/tests/ --durations=20

for f in hypothesis-extra/*/manage.py; do
    d=$(dirname $f)
    pushd $d
        python manage.py test
    popd
done
