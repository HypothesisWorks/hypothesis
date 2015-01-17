from abc import abstractmethod


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
