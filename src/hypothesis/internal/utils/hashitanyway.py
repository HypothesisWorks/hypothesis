from hypothesis.internal.utils.fixers import actually_equal
from hypothesis.internal.compat import text_type, binary_type
from hypothesis.internal.extmethod import ExtMethod

hash_everything_method = ExtMethod()


@hash_everything_method.extend(int)
@hash_everything_method.extend(float)
@hash_everything_method.extend(binary_type)
@hash_everything_method.extend(text_type)
@hash_everything_method.extend(bool)
def normal_hash(x):
    return hash(x)


@hash_everything_method.extend(type)
def type_hash(x):
    return hash(x.__name__)


@hash_everything_method.extend(object)
def generic_hash(x):
    h = hash(type(x).__name__)
    try:
        h ^= hash(len(x))
    except (TypeError, AttributeError):
        pass
    try:
        iter(x)
    except (TypeError, AttributeError):
        return h

    for y in x:
        h ^= hash_everything(y)
    return h


def hash_everything(l):
    return hash_everything_method(type(l), l)


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
