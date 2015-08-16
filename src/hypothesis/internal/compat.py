# coding=utf-8

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# Most of this work is copyright (C) 2013-2015 David R. MacIver
# (david@drmaciver.com), but it contains contributions by other. See
# https://github.com/DRMacIver/hypothesis/blob/master/CONTRIBUTING.rst for a
# full list of people who may hold copyright, and consult the git log if you
# need to determine who owns an individual contribution.

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

# pylint: skip-file

from __future__ import division, print_function, absolute_import

import sys
import math
import platform
import importlib
from decimal import Context, Decimal, Inexact

try:
    from collections import OrderedDict, Counter
except ImportError:  # pragma: no cover
    from ordereddict import OrderedDict
    from counter import Counter


PY3 = sys.version_info[0] == 3
BAD_PY3 = PY3 and (sys.version_info[1] <= 2)
PYPY = platform.python_implementation() == u'PyPy'
PY26 = sys.version_info[:2] == (2, 6)


if PY26:
    _special_floats = {
        float(u'inf'): Decimal(u'Infinity'),
        float(u'-inf'): Decimal(u'-Infinity'),
    }

    def float_to_decimal(f):
        """Convert a floating point number to a Decimal with no loss of
        information."""
        if f in _special_floats:
            return _special_floats[f]
        elif math.isnan(f):
            return Decimal(u'NaN')
        n, d = f.as_integer_ratio()
        numerator, denominator = Decimal(n), Decimal(d)
        ctx = Context(prec=60)
        result = ctx.divide(numerator, denominator)
        while ctx.flags[Inexact]:
            ctx.flags[Inexact] = False
            ctx.prec *= 2
            result = ctx.divide(numerator, denominator)
        return result
else:
    def float_to_decimal(f):
        return Decimal(f)


if PY3:
    text_type = str
    binary_type = bytes
    hrange = range
    ARG_NAME_ATTRIBUTE = u'arg'
    integer_types = (int,)
    hunichr = chr
    from functools import reduce

    def unicode_safe_repr(x):
        return repr(x)
else:
    def unicode_safe_repr(x):
        try:
            r = type(x).__repr__(x)
        except TypeError:
            # Workaround for https://bitbucket.org/pypy/pypy/issues/2083/
            r = repr(x)
        if isinstance(r, unicode):
            return r
        else:
            return r.decode(a_good_encoding())

    text_type = unicode
    binary_type = str

    def hrange(start_or_finish, finish=None, step=None):
        try:
            if step is None:
                if finish is None:
                    return xrange(start_or_finish)
                else:
                    return xrange(start_or_finish, finish)
            else:
                return xrange(start_or_finish, finish, step)
        except OverflowError:
            if step == 0:
                raise ValueError(u'step argument may not be zero')
            if step is None:
                step = 1
            if finish is not None:
                start = start_or_finish
            else:
                start = 0
                finish = start_or_finish
            assert step != 0
            if step > 0:
                def shimrange():
                    i = start
                    while i < finish:
                        yield i
                        i += step
            else:
                def shimrange():
                    i = start
                    while i > finish:
                        yield i
                        i += step
            return shimrange()

    ARG_NAME_ATTRIBUTE = u'id'
    integer_types = (int, long)
    hunichr = unichr
    reduce = reduce


def a_good_encoding():
    result = sys.getdefaultencoding()
    if result == u'ascii':
        return u'utf-8'
    else:
        return result


def to_unicode(x):
    if isinstance(x, text_type):
        return x
    else:
        return x.decode(a_good_encoding())


def qualname(f):
    try:
        return f.__qualname__
    except AttributeError:
        pass
    try:
        return f.im_class.__name__ + u'.' + f.__name__
    except AttributeError:
        return f.__name__


importlib_invalidate_caches = getattr(
    importlib, u'invalidate_caches', lambda: ())
