from abc import abstractmethod
import sqlite3


class Backend(object):
    """
    Interface class for storage systems. Simple key / multiple value store.
    """

    @abstractmethod
    def save(self, key, value):
        """
        Save a single value matching this key
        """

    @abstractmethod
    def fetch(self, key):
        """
        yield the values matching this key, ignoring duplicates
        """


class InMemoryBackend(Backend):
    """
    The default implementation.

    This backend simply saves the values in a dict. It's not very useful
    except in that it may speed up cases where the same example can fail
    multiple tests.
    """
    def __init__(self):
        self.data = {}

    def save(self, key, value):
        self.data.setdefault(key, set()).add(value)

    def fetch(self, key):
        for v in self.data.get(key, ()):
            yield v


class SQLiteBackend(Backend):
    def __init__(self, path):
        self.connection = sqlite3.connect(path)
        self.db_created = False

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
