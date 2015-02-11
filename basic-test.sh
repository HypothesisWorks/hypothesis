#!/bin/bash
set -e -o xtrace

pip install hypothesis-extra/*/
python -m pytest --capture=no --strict tests/ hypothesis-extra/*/tests/
