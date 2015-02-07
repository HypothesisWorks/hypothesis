#!/bin/bash

set -o xtrace -e


find src tests -name '*.py' | xargs pyformat -i
git diff --exit-code
flake8 src tests --exclude=compat.py,test_reflection.py --ignore=E731
rst-lint README.rst
