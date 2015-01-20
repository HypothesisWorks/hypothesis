set -e -o xtrace

export PYTHONDONTWRITEBYTECODE=x
export HYPOTHESIS_DATABASE_FILE=$(mktemp --suffix=.db)
HYPOTHESIS_DATABASE_FILE=hypothesis.db PYTHONPATH=src python -u -m coverage run -a --branch --include 'src/hypothesis/*' --omit 'src/hypothesis/settings.py,src/hypothesis/internal/compat.py' $(which py.test) -v tests --ignore=tests/test_recursively.py
PYTHONPATH=src python -c '
from __future__ import print_function

from hypothesis.database import ExampleDatabase
from hypothesis.database.backend import SQLiteBackend
import os
import sys
database_file = os.getenv("HYPOTHESIS_DATABASE_FILE")
print("Database file is", database_file)

db = ExampleDatabase(
    backend=SQLiteBackend(database_file))
data = list(db.storage_for((((int,), {}),)).fetch())
if not data:
    print("No integer examples in database")
    sys.exit(1)
'
HYPOTHESIS_DATABASE_FILE=hypothesis.db PYTHONPATH=src python -u -m coverage run -a --branch --include 'src/hypothesis/*' --omit 'src/hypothesis/settings.py,src/hypothesis/internal/compat.py' $(which py.test) -v tests --ignore=tests/test_recursively.py
