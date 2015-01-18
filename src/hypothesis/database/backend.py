from abc import abstractmethod
import sqlite3
from hypothesis.internal.compat import text_type


class Backend(object):

    """Interface class for storage systems.

    Simple text key -> value mapping. values are of the type returned by
    data_type() but keys are always unicode text (str in python 3, unicode in
    python 2).

    Every (key, value) pair appears at most once. Saving a duplicate will just
    silently do nothing.

    """

    @abstractmethod
    def data_type(self):
        """Returns the type of data that is suitable for values in this DB."""

    @abstractmethod
    def save(self, key, value):
        """Save a single value matching this key."""

    @abstractmethod
    def fetch(self, key):
        """yield the values matching this key."""


class SQLiteBackend(Backend):

    def __init__(self, path=':memory:'):
        self.connection = sqlite3.connect(path)
        self.db_created = False

    def data_type(self):
        return text_type

    def save(self, key, value):
        self.create_db_if_needed()
        cursor = self.connection.cursor()
        try:
            cursor.execute("""
                insert into hypothesis_data_mapping(key, value)
                values(?, ?)
            """, (key, value))
            cursor.close()
            self.connection.commit()
        except sqlite3.IntegrityError:
            pass

    def fetch(self, key):
        self.create_db_if_needed()
        cursor = self.connection.cursor()
        cursor.execute("""
            select value from hypothesis_data_mapping
            where key = ?
        """, (key,))
        for (value,) in cursor:
            yield value

    def create_db_if_needed(self):
        if self.db_created:
            return
        cursor = self.connection.cursor()
        cursor.execute("""
            create table if not exists hypothesis_data_mapping(
                key text,
                value text,
                unique(key, value)
            )
        """)
        cursor.close()
        self.connection.commit()
        self.db_created = True
