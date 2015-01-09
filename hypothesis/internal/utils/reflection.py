import inspect
from six.moves import xrange


def convert_keyword_arguments(function, args, kwargs):
    """
    Returns a pair of a tuple and a dictionary which would be equivalent
    passed as positional and keyword args to the function. Unless function has
    **kwargs the dictionary will always be empty.
    """
    argspec = inspect.getargspec(function)
    new_args = []
    kwargs = dict(kwargs)

    defaults = {}

    if argspec.defaults:
        for name, value in zip(
            argspec.args[-len(argspec.defaults):], argspec.defaults
        ):
            defaults[name] = value

    n = max(len(args), len(argspec.args))

    for i in xrange(n):
        if i < len(args):
            new_args.append(args[i])
        else:
            arg_name = argspec.args[i]
            if arg_name in kwargs:
                new_args.append(kwargs.pop(arg_name))
            elif arg_name in defaults:
                new_args.append(defaults[arg_name])
            else:
                raise TypeError("No value provided for argument %r" % (
                    arg_name
                ))

    if kwargs and not argspec.keywords:
        if len(kwargs) > 1:
            raise TypeError("%s() got unexpected keyword arguments %s" % (
                function.__name__, ', '.join(map(repr, kwargs))
            ))
        else:
            bad_kwarg = next(iter(kwargs))
            raise TypeError("%s() got an unexpected keyword argument %r" % (
                function.__name__, bad_kwarg
            ))
    return tuple(new_args), kwargs
