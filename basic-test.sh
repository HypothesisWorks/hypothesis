#!/bin/bash
set -e -o xtrace

if [ "$(python -c 'import platform; print(platform.python_implementation())')" == "PyPy" ]; then
    pypy -m pip install git+https://bitbucket.org/pypy/numpy.git
fi

for extra in datetime fakefactory pytest django numpy; do
    pip install --upgrade hypothesis-extra/hypothesis-$extra/
    python -m pytest hypothesis-extra/hypothesis-$extra/tests --durations=20
done

pushd hypothesis-extra/hypothesis-django
    python manage.py test
popd

