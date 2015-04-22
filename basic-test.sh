#!/bin/bash
set -e -o xtrace

python -m pytest --capture=no --strict tests/ --durations=20

for extra in "datetime fakefactory pytest django"; do
    pip install --upgrade hypothesis-extra/hypothesis-$extra/
    python -m pytest hypothesis-extra/hypothesis-$extra tests --durations=20
done

pushd hypothesis-extra/hypothesis-django
    python manage.py test
popd

if [ "$(python -c 'import platform; print(platform.python_implementation())')" != "PyPy" ]; then
    pip install --upgrade hypothesis-extra/hypothesis-numpy/
    python -m pytest hypothesis-extra/hypothesis-numpy tests
fi
