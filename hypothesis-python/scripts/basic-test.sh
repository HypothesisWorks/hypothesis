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


PYTEST="python -bb -X dev -m pytest -nauto --durations-min=1.0"

# Run all the no-extra-dependency tests for this version (except slow nocover tests)
$PYTEST tests/cover tests/pytest

# Run tests for each extra module while the requirements are installed
pip install ".[pytz, dateutil, zoneinfo]"
$PYTEST tests/datetime/
pip uninstall -y pytz python-dateutil

pip install ".[dpcontracts]"
$PYTEST tests/dpcontracts/
pip uninstall -y dpcontracts

# use pinned redis version instead of inheriting from fakeredis
pip install "$(grep '^redis==' ../requirements/coverage.txt)"
pip install "$(grep 'fakeredis==' ../requirements/coverage.txt)"
$PYTEST tests/redis/
pip uninstall -y redis fakeredis

pip install "$(grep 'typing-extensions==' ../requirements/coverage.txt)"
$PYTEST tests/typing_extensions/
pip uninstall -y typing_extensions

pip install ".[lark]"
pip install "$(grep -m 1 -oE 'lark>=([0-9.]+)' ../hypothesis-python/pyproject.toml | tr '>' =)"
$PYTEST -Wignore tests/lark/
pip install "$(grep 'lark==' ../requirements/coverage.txt)"
$PYTEST tests/lark/
pip uninstall -y lark

if [ "$(python -c $'import platform, sys; print(sys.version_info.releaselevel == \'final\' and platform.python_implementation() not in ("PyPy", "GraalVM"))')" = "True" ] ; then
  pip install ".[codemods,cli]"
  $PYTEST tests/codemods/
  pip uninstall -y libcst click

  if [ "$(python -c 'import sys; print(sys.version_info[:2] == (3, 9))')" = "True" ] ; then
    # Per NEP-29, this is the last version to support Python 3.9
    pip install numpy==2.0.2
  else
    pip install "$(grep 'numpy==' ../requirements/coverage.txt)"
  fi

  pip install "$(grep -E 'black(==| @)' ../requirements/coverage.txt)"
  $PYTEST tests/ghostwriter/
  pip uninstall -y black numpy
fi

if [ "$(python -c 'import sys; print(sys.version_info[:2] == (3, 10))')" = "False" ] ; then
  exit 0
fi

$PYTEST tests/nocover/

# Run some tests without docstrings or assertions, to catch bugs
# like issue #822 in one of the test decorators.  See also #1541.
PYTHONOPTIMIZE=2 $PYTEST \
    -W'ignore:assertions not in test modules or plugins will be ignored because assert statements are not executed by the underlying Python interpreter:pytest.PytestConfigWarning' \
    -W'ignore:Module already imported so cannot be rewritten:pytest.PytestAssertRewriteWarning' \
    tests/cover/test_testdecorators.py

case "$(python -c 'import platform; print(platform.python_implementation())')" in
  PyPy|GraalVM)
    ;;
  *)
    pip install .[django]
    HYPOTHESIS_DJANGO_USETZ=TRUE python -m tests.django.manage test tests.django
    HYPOTHESIS_DJANGO_USETZ=FALSE python -m tests.django.manage test tests.django
    pip uninstall -y django pytz

    pip install "$(grep 'numpy==' ../requirements/coverage.txt)"
    $PYTEST tests/array_api
    $PYTEST tests/numpy

    pip install "$(grep 'pandas==' ../requirements/coverage.txt)"
    $PYTEST tests/pandas
esac
