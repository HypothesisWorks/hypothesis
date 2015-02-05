"""This is a module for functions I consider to be designed to work around
Python doing entirely the wrong thing.

You can imagine how grumpy I was when I wrote it.

"""

from hypothesis.internal.compat import text_type, binary_type, integer_types
import math
from hypothesis.internal.extmethod import ExtMethod


equality = ExtMethod()


primitives = [
    int, float, bool, type, text_type, binary_type
] + list(integer_types)


@equality.extend(object)
def generic_equality(x, y, fuzzy):
    try:
        if len(x) != len(y):
            return False
    except (TypeError, AttributeError):
        pass
    ix = None
    iy = None
    try:
        ix = iter(x)
        iy = iter(y)
    except TypeError:
        pass
    assert (ix is None) == (iy is None)
    if ix is not None:
        for u, v in zip(ix, iy):
            if not actually_equal(u, v, fuzzy):
                return False
        return True
    return x == y


@equality.extend(int)
@equality.extend(bool)
@equality.extend(type)
@equality.extend(text_type)
@equality.extend(binary_type)
def primitive_equality(x, y, fuzzy):
    return x == y


@equality.extend(float)
def float_equality(x, y, fuzzy=False):
    if math.isnan(x) and math.isnan(y):
        return True
    if x == y:
        return True
    return fuzzy and (repr(x) == repr(y))


@equality.extend(complex)
def complex_equality(x, y, fuzzy=False):
    return (
        float_equality(x.real, y.real, fuzzy) and
        float_equality(x.imag, y.imag, fuzzy)
    )


@equality.extend(tuple)
@equality.extend(list)
def sequence_equality(x, y, fuzzy=False):
    if len(x) != len(y):
        return False
    for u, v in zip(x, y):
        if not actually_equal(u, v, fuzzy):
            return False
    return True


@equality.extend(set)
@equality.extend(frozenset)
def set_equality(x, y, fuzzy=False):
    if len(x) != len(y):
        return False
    for u in x:
        if not actually_in(u, y):
            return False
    return True


@equality.extend(dict)
def dict_equality(x, y, fuzzy=False):
    if len(x) != len(y):
        return False
    for k, v in x.items():
        if k not in y:
            return False
        if not actually_equal(x[k], y[k], fuzzy):
            return False
    return True


def actually_equal(x, y, fuzzy=False):
    """
    Look, this function is terrible. I know it's terrible. I'm sorry.
    Hypothesis relies on a more precise version of equality than python uses
    and in particular is broken by things like frozenset() == set() because
    that behaviour is just broken.

    Unfortunately this means that we have to define our own equality. We do
    our best to respect the equality defined on types but there's only so much
    we can do.

    If fuzzy is True takes a slightly laxer approach around e.g. floating point
    equality.
    """
    if x is y:
        return True
    if type(x) != type(y):
        return False
    return equality(type(x), x, y, fuzzy)


def actually_in(x, ys, fuzzy=False):
    return any(actually_equal(x, y, fuzzy) for y in ys)


def real_index(xs, y, fuzzy=False):
    i = xs.index(y)
    if actually_equal(xs[i], y, fuzzy):
        return i
    else:
        i = 0
        while i < len(xs):
            if actually_equal(xs[i], y, fuzzy):
                return i
            i += 1
        raise ValueError('%r is not in list' % (y))


def is_nasty_float(x):
    return math.isnan(x) or math.isinf(x)


nice_string_method = ExtMethod()


@nice_string_method.extend(object)
def generic_string(xs):
    if hasattr(xs, '__name__'):
        return xs.__name__
    try:
        d = xs.__dict__
    except AttributeError:
        return repr(xs)

    if getattr(xs.__repr__, '__objclass__', None) != object:
        return repr(xs)
    else:
        return '%s(%s)' % (
            xs.__class__.__name__,
            ', '.join(
                '%s=%s' % (k2, nice_string(v2)) for k2, v2 in d.items()
            )
        )


@nice_string_method.extend(type)
def type_string(xs):
    return xs.__name__


@nice_string_method.extend(float)
def float_string(xs):
    if is_nasty_float(xs):
        return 'float(%r)' % (str(xs),)
    else:
        return repr(xs)


@nice_string_method.extend(complex)
def complex_string(x):
    if is_nasty_float(x.real) or is_nasty_float(x.imag):
        r = repr(x)
        if r[0] == '(' and r[-1] == ')':
            r = r[1:-1]
        return 'complex(%r)' % (r,)
    else:
        return repr(x)


@nice_string_method.extend(list)
def list_string(xs):
    return '[%s]' % (', '.join(map(nice_string, xs)))


@nice_string_method.extend(set)
def set_string(xs):
    if xs:
        return '{%s}' % (', '.join(sorted(map(nice_string, xs))))
    else:
        return repr(xs)


@nice_string_method.extend(frozenset)
def frozenset_string(xs):
    if xs:
        return 'frozenset({%s})' % (', '.join(sorted(map(nice_string, xs))))
    else:
        return repr(xs)


@nice_string_method.extend(tuple)
def tuple_string(xs):
    if hasattr(xs, '_fields'):
        return '%s(%s)' % (
            xs.__class__.__name__,
            ', '.join(
                '%s=%s' % (f, nice_string(getattr(xs, f)))
                for f in xs._fields))
    else:
        core = ', '.join(map(nice_string, xs))
        if len(xs) == 1:
            core += ','
        return '(%s)' % (core,)


@nice_string_method.extend(dict)
def dict_string(xs):
    return '{' + ', '.join(sorted([
        nice_string(k1) + ':' + nice_string(v1)
        for k1, v1 in xs.items()
    ])) + '}'


def nice_string(xs):
    """Take a descriptor and produce a nicer string representation of it than
    repr.

    In particular this is designed to work around the problem that the
    repr for type objects is nasty.

    """
    return nice_string_method(type(xs), xs)
