#!/bin/bash
set -e -o xtrace

HERE="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$HERE/.."

python -c '
import os
for k, v in sorted(dict(os.environ).items()):
    print("%s=%s" % (k, v))
'

pip install .


PYTEST="python -m pytest -n2"

$PYTEST --runpytest=subprocess tests/pytest

# Run some tests without docstrings or assertions, to catch bugs
# like issue #822 in one of the test decorators.  See also #1541.
PYTHONOPTIMIZE=2 $PYTEST tests/cover/test_testdecorators.py

pip install ".[pytz, dateutil]"
$PYTEST tests/datetime/
pip uninstall -y pytz python-dateutil

pip install ".[dpcontracts]"
$PYTEST tests/dpcontracts/
pip uninstall -y dpcontracts

if [ "$(python -c 'import sys; print(sys.version_info[0] == 2)')" = "True" ] ; then
  $PYTEST "tests/py2"
else
  $PYTEST "tests/py3"
fi

# We run a reduced set of tests on the macOS CI so that it runs in vaguely
# reasonable time.
if [ "$CIRCLECI" = true ]; then
  echo Skipping the rest of the test suite on CircleCI.
  exit 0
fi

if [ "$(python -c 'import sys; print(sys.version_info[:2] in ((2, 7), (3, 6)))')" = "False" ] ; then
  exit 0
fi

$PYTEST tests/nocover/

if [ "$(python -c 'import platform; print(platform.python_implementation())')" != "PyPy" ]; then
  pip install .[django]
  HYPOTHESIS_DJANGO_USETZ=TRUE python -m tests.django.manage test tests.django
  HYPOTHESIS_DJANGO_USETZ=FALSE python -m tests.django.manage test tests.django
  pip uninstall -y django pytz

  pip install numpy
  $PYTEST tests/numpy

  pip install pandas
  $PYTEST tests/pandas

  pip uninstall -y numpy pandas
fi
