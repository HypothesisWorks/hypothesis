from hypothesis.internal.utils.fixers import actually_equal


def hash_everything(l):
    try:
        return hash(l)
    except TypeError:
        h = hash(l.__class__)
        try:
            xs = iter(l)
        except TypeError:
            return h

        for x in xs:
            h = h ^ hash_everything(x)
        return h


class HashItAnyway(object):

    def __init__(self, wrapped):
        self.wrapped = wrapped
        self.h = hash_everything(wrapped)

    def __eq__(self, other):
        return (isinstance(other, HashItAnyway) and
                self.h == other.h and
                actually_equal(self.wrapped, other.wrapped))

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return self.h

    def __repr__(self):
        return 'HashItAnyway(%s)' % repr(self.wrapped)
