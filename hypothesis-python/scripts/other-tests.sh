#!/bin/bash
set -e -o xtrace

HERE="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$HERE/.."

pip install .


PYTEST="python -bb -X dev -m pytest -nauto --durations-min=1.0"

# Run some tests without docstrings or assertions, to catch bugs
# like issue #822 in one of the test decorators.  See also #1541.
PYTHONOPTIMIZE=2 $PYTEST \
    -W'ignore:assertions not in test modules or plugins will be ignored because assert statements are not executed by the underlying Python interpreter:pytest.PytestConfigWarning' \
    -W'ignore:Module already imported so cannot be rewritten:pytest.PytestAssertRewriteWarning' \
    tests/cover/test_testdecorators.py

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
pip install "$(grep 'typing-extensions==' ../requirements/coverage.txt)"
$PYTEST tests/redis/
pip uninstall -y redis fakeredis

$PYTEST tests/typing_extensions/
if [[ "$HYPOTHESIS_PROFILE" != "crosshair" ]]; then
  pip uninstall -y typing_extensions
fi

pip install "$(grep 'annotated-types==' ../requirements/coverage.txt)"
$PYTEST tests/test_annotated_types.py
pip uninstall -y annotated-types

pip install ".[lark]"
pip install "$(grep -m 1 -oE 'lark>=([0-9.]+)' ../hypothesis-python/pyproject.toml | tr '>' =)"
$PYTEST -Wignore tests/lark/
pip install "$(grep 'lark==' ../requirements/coverage.txt)"
$PYTEST tests/lark/
pip uninstall -y lark

if [ "$(python -c $'import platform, sys; print(sys.version_info.releaselevel == \'final\' and platform.python_implementation() not in ("PyPy", "GraalVM"))')" = "True" ] ; then
  pip install ".[codemods,cli]"
  $PYTEST tests/codemods/

  if [ "$(python -c 'import sys; print(sys.version_info[:2] == (3, 9))')" = "True" ] ; then
    # Per NEP-29, this is the last version to support Python 3.9
    pip install numpy==2.0.2
  else
    pip install "$(grep 'numpy==' ../requirements/coverage.txt)"
  fi

  pip install "$(grep -E 'black(==| @)' ../requirements/coverage.txt)"
  $PYTEST tests/patching/
  pip uninstall -y libcst

  $PYTEST tests/ghostwriter/
  pip uninstall -y black

  if [ "$HYPOTHESIS_PROFILE" != "crosshair" ] && [ "$(python -c "import platform; print(platform.python_implementation() not in {'PyPy', 'GraalVM'})")" = "True" ] ; then
    $PYTEST tests/array_api tests/numpy
  fi
fi
