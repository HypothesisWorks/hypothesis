#!/bin/bash

set -o xtrace -e

python enforce_header.py
isort -p hypothesis -ls -m 2 -w 75 \
    -a  "from __future__ import absolute_import, print_function, unicode_literals, division" \
    -rc src tests hypothesis-extra/*/{src,tests}
find hypothesis-extra/*/{src,tests} src tests -name '*.py' | xargs pyformat -i
git diff --exit-code
flake8 src tests --exclude=compat.py,test_reflection.py --ignore=E731
for f in ./README.rst ./hypothesis-extra/*/README.rst; do
  rst-lint $f
done

