#!/bin/bash
set -e -o xtrace

# We run a reduced set of tests on OSX mostly so the CI runs in vaguely
# reasonable time.
if [[ "$(uname -s)" == 'Darwin' ]]; then
    DARWIN=true
else
    DARWIN=false
fi

python -c '
import os
for k, v in sorted(dict(os.environ).items()):
    print("%s=%s" % (k, v))
'

pip install .


if [ "$(python -c 'import sys; print(sys.version_info[:2] == (2, 6))')" == "True" ] ; then
    pip install --upgrade ./hypothesislegacysupport
fi

PYTEST="python -m pytest"

$PYTEST tests/cover

if [ "$(python -c 'import sys; print(sys.version_info[0] == 2)')" = "True" ] ; then
    $PYTEST tests/py2
else
    $PYTEST tests/py3
fi

$PYTEST --runpytest=subprocess tests/pytest

if [ "$DARWIN" != true ]; then
  for f in tests/nocover/test_*.py; do
    $PYTEST $f
  done
fi


pip install .[datetime]
$PYTEST tests/datetime/
pip uninstall -y pytz

if [ "$DARWIN" = true ]; then
  exit 0
fi

# fake-factory doesn't have a correct universal wheel
pip install --no-use-wheel .[fakefactory]
$PYTEST tests/fakefactory/

if [ "$(python -c 'import platform; print(platform.python_implementation())')" != "PyPy" ]; then
  if [ "$(python -c 'import sys; print(sys.version_info[:2] <= (2, 6))')" != "True" ] ; then
  if [ "$(python -c 'import sys; print(sys.version_info[0] == 2 or sys.version_info[:2] >= (3, 4))')" == "True" ] ; then
    pip install .[django]
    python -m tests.django.manage test tests.django
    pip uninstall -y django fake-factory
  fi
  fi

  if [ "$(python -c 'import sys; print(sys.version_info[:2] < (3, 5))')" = "True" ] ; then
    if [ "$(python -c 'import sys; print(sys.version_info[:2] <= (2, 6))')" != "True" ] ; then
      pushd $HOME
        pip wheel numpy==1.9.2
      popd
      pip install --find-links=$HOME/wheelhouse numpy==1.9.2
    else
      pip install numpy==1.9.2
    fi
    $PYTEST tests/numpy
    pip uninstall -y numpy
  fi
fi
