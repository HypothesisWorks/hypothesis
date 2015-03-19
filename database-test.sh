#!/bin/bash

set -o xtrace -e

export PYTHONDONTWRITEBYTECODE=x
export HYPOTHESIS_DATABASE_FILE=$(python -c 'import tempfile; print(tempfile.mkstemp(suffix=".db")[-1])')
rm $HYPOTHESIS_DATABASE_FILE
python -u -m pytest -v tests/test_testdecorators.py
python -c '
from __future__ import division, print_function, absolute_import, \
    unicode_literals

from hypothesis.database import ExampleDatabase
from hypothesis.database.backend import SQLiteBackend
import os
import sys
database_file = os.getenv("HYPOTHESIS_DATABASE_FILE")
print("Database file is", database_file)

db = ExampleDatabase(
    backend=SQLiteBackend(database_file))
data = list(db.storage_for((((), {"x": int}),)).fetch())
data += list(db.storage_for((((), {b"x": int}),)).fetch())
if not data:
    print("No integer examples in database")
    sys.exit(1)
'
python -u -m pytest -v tests/test_testdecorators.py
