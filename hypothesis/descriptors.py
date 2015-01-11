from collections import namedtuple


Just = namedtuple('Just', 'value')
just = Just


OneOf = namedtuple('OneOf', 'elements')


def one_of(args):
    args = tuple(args)
    if not args:
        raise ValueError('one_of requires at least one value to choose from')
    if len(args) == 1:
        return args[0]
    return OneOf(args)


IntegerRange = namedtuple('IntegerRange', ('start', 'end'))


def integers_in_range(start, end):
    return IntegerRange(start, end)


FloatRange = namedtuple('FloatRange', ('start', 'end'))


def floats_in_range(start, end):
    return FloatRange(start, end)
