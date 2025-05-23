Write a custom Hypothesis database
==================================

To define your own |ExampleDatabase| class, implement the |ExampleDatabase.save|, |ExampleDatabase.fetch|, and |ExampleDatabase.delete| methods.

For example, here's a simple database class that uses :mod:`sqlite <sqlite3>` as the backing data store:

.. code-block:: python

    import sqlite3
    from collections.abc import Iterable

    from hypothesis.database import ExampleDatabase

    class SQLiteExampleDatabase(ExampleDatabase):
        def __init__(self, db_path: str):
            self.conn = sqlite3.connect(db_path)

            self.conn.execute(
                """
                CREATE TABLE examples (
                    key BLOB,
                    value BLOB,
                    UNIQUE (key, value)
                )
            """
            )

        def save(self, key: bytes, value: bytes) -> None:
            self.conn.execute(
                "INSERT OR IGNORE INTO examples VALUES (?, ?)",
                (key, value),
            )

        def fetch(self, key: bytes) -> Iterable[bytes]:
            cursor = self.conn.execute("SELECT value FROM examples WHERE key = ?", (key,))
            yield from [value[0] for value in cursor.fetchall()]

        def delete(self, key: bytes, value: bytes) -> None:
            self.conn.execute(
                "DELETE FROM examples WHERE key = ? AND value = ?",
                (key, value),
            )

Database classes are not required to implement |ExampleDatabase.move|. The default implementation of a move is a |ExampleDatabase.delete| of the value in the old key, followed by a |ExampleDatabase.save| of the value in the new key. You can override |ExampleDatabase.move| to override this behavior, if for instance the backing store offers a more efficient move implementation.

Change listening
----------------

To support change listening in a database class, you should call ``self._broadcast_change(event)`` whenever a value is saved, deleted, or moved in the backing database store. How you track this depends on the details of the database class. For instance, in |DirectoryBasedExampleDatabase|, Hypothesis installs a filesystem monitor via :pypi:`watchdog` in order to broadcast change events.

Two related useful methods are ``ExampleDatabase._start_listening`` and ``ExampleDatabase._stop_listening``, which a database class can override to know when to start or stop expensive listening operations. See source code for documentation.
