"""This is a module for functions I consider to be designed to work around
Python doing entirely the wrong thing.

You can imagine how grumpy I was when I wrote it.

"""

from hypothesis.internal.compat import text_type, binary_type, integer_types
import math

unordered_collections = [set, frozenset]
dict_like_collections = [dict]
primitives = [
    int, float, bool, type, text_type, binary_type
] + list(integer_types)


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

    # Now the bad part begins
    if isinstance(x, float):
        if math.isnan(x) and math.isnan(y):
            return True
        if fuzzy:
            return repr(x) == repr(y)
        return x == y

    if isinstance(x, tuple(primitives)):
        if x == y:
            return True

        return False

    if isinstance(x, complex):
        return (
            actually_equal(x.real, y.real, fuzzy) and
            actually_equal(x.imag, y.imag, fuzzy)
        )

    lx = -1
    ly = -1
    try:
        lx = len(x)
        ly = len(y)
    except (TypeError, AttributeError):
        pass

    assert (lx < 0) == (ly < 0)
    if lx >= 0 and lx != ly:
        return False

    if isinstance(x, tuple(unordered_collections)):
        for xe in x:
            if not actually_in(xe, y, fuzzy):
                return False
        return True
    try:
        xi = iter(x)
        yi = iter(y)
    except TypeError:
        return x == y

    if isinstance(x, tuple(dict_like_collections)):
        for xk in xi:
            xv = x[xk]
            try:
                yv = y[xk]
            except KeyError:
                return False
            if not actually_equal(xv, yv, fuzzy):
                return False
        return True

    for xv, yv in zip(xi, yi):
        if not actually_equal(xv, yv, fuzzy):
            return False
    return True


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
