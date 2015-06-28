#!/bin/bash
set -e -o xtrace

python -c '
import os
for k, v in sorted(dict(os.environ).items()):
    print("%s=%s" % (k, v))
'
python -u setup.py test

for extra in datetime fakefactory pytest ; do
    pip install --upgrade hypothesis-extra/hypothesis-$extra/
done

for extra in datetime fakefactory pytest ; do
    python -m pytest hypothesis-extra/hypothesis-$extra/tests/
done

if [ "$(python -c 'import platform; print(platform.python_implementation())')" != "PyPy" ]; then
    pip install --upgrade hypothesis-extra/hypothesis-numpy/
    python -u -m pytest hypothesis-extra/hypothesis-numpy/tests --durations=20
fi

if [ "$(python -c 'import sys; print(sys.version_info[:2] <= (2, 6))')" != "True" ] ; then
    pip install --upgrade hypothesis-extra/hypothesis-django/
    pushd hypothesis-extra/hypothesis-django
        python -u manage.py test
    popd
fi

