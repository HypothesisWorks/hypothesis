from __future__ import division, print_function, absolute_import, \
    unicode_literals


class IdKey(object):

    def __init__(self, value):
        self.value = value

    def __eq__(self, other):
        return (type(other) == IdKey) and (self.value is other.value)

    def __ne__(self, other):
        return not (self.__eq__(other))

    def __hash__(self):
        return hash(id(self.value))


class IdentitySet(object):

    def __init__(self):
        self.data = {}

    def __contains__(self, value):
        key = IdKey(value)
        return self.data.get(key, 0) > 0

    def add(self, value):
        key = IdKey(value)
        self.data[key] = self.data.get(key, 0) + 1

    def remove(self, value):
        key = IdKey(value)
        self.data[key] = self.data.get(key, 0) - 1
