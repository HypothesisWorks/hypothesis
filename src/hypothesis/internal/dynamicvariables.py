import threading
from contextlib import contextmanager


class DynamicVariable(object):

    def __init__(self, default):
        self.default = default
        self.data = threading.local()

    @property
    def value(self):
        return getattr(self.data, 'value', self.default)

    @contextmanager
    def with_value(self, value):
        old_value = self.value
        try:
            self.data.value = value
            yield
        finally:
            self.data.value = old_value
