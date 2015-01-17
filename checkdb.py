from __future__ import print_function

from hypothesis.database import ExampleDatabase
from hypothesis.database.backend import SQLiteBackend
import sys

db = ExampleDatabase(backend=SQLiteBackend("hypothesis.db"))
data = list(db.storage_for((((int,), {}),)).fetch())
if not data:
    print("No integer examples in database")
    sys.exit(1)
