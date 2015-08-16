#!/bin/bash

set -o xtrace -e

export LC_ALL=en_GB.UTF-8

python scripts/enforce_header.py
isort -p hypothesis -ls -m 2 -w 75 \
    -a  "from __future__ import absolute_import, print_function, division" \
    -rc src tests examples hypothesis-extra/*/{src,tests}
find hypothesis-extra/*/{src,tests} src tests examples -name '*.py' | xargs pyformat -i
git diff --exit-code
flake8 src tests --exclude=compat.py,test_reflection.py,tests/py2 --ignore=E731,E721
