#!/bin/bash
set -e -o xtrace

for extra in datetime fakefactory pytest django ; do
    pip install --upgrade hypothesis-extra/hypothesis-$extra/
    python -m pytest hypothesis-extra/hypothesis-$extra/tests --durations=20
done

if [ "$(python -c 'import platform; print(platform.python_implementation())')" != "PyPy" ]; then
    pip install --upgrade hypothesis-extra/hypothesis-numpy/
    python -m pytest hypothesis-extra/hypothesis-numpy/tests --durations=20
fi

pushd hypothesis-extra/hypothesis-django
    python manage.py test
popd

