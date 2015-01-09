from collections import namedtuple


Just = namedtuple('Just', 'value')
just = Just


OneOf = namedtuple('OneOf', 'elements')


def one_of(args):
    args = list(args)
    if not args:
        raise ValueError('one_of requires at least one value to choose from')
    if len(args) == 1:
        return args[0]
    return OneOf(args)
