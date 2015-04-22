#!/bin/bash
set -e -o xtrace

for extra in datetime fakefactory pytest ; do
    pip install --upgrade hypothesis-extra/hypothesis-$extra/
done

if [ "$(python -c 'import platform; print(platform.python_implementation())')" != "PyPy" ]; then
    pip install --upgrade hypothesis-extra/hypothesis-numpy/
    python -m pytest hypothesis-extra/hypothesis-numpy/tests --durations=20
fi

pip install --upgrade hypothesis-extra/hypothesis-django/

pushd hypothesis-extra/hypothesis-django
    python manage.py test
popd

