# coding=utf-8

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# Most of this work is copyright (C) 2013-2015 David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
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
from collections import namedtuple

try:
    from collections import OrderedDict, Counter
except ImportError:  # pragma: no cover
    from ordereddict import OrderedDict
    from counter import Counter


PY3 = sys.version_info[0] == 3
PYPY = platform.python_implementation() == u'PyPy'
PY26 = sys.version_info[:2] == (2, 6)
NO_ARGSPEC = sys.version_info[:2] >= (3, 5)
HAS_SIGNATURE = sys.version_info[:2] >= (3, 3)

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

FakeArgSpec = namedtuple(
    'ArgSpec', ('args', 'varargs', 'keywords', 'defaults'))


def signature_argspec(f):
    from inspect import signature, Parameter, _empty
    try:
        if NO_ARGSPEC:
            sig = signature(f, follow_wrapped=False)
        else:
            sig = signature(f)
    except ValueError:
        raise TypeError('unsupported callable')
    args = list(
        k
        for k, v in sig.parameters.items()
        if v.kind in (
            Parameter.POSITIONAL_ONLY, Parameter.POSITIONAL_OR_KEYWORD))
    varargs = None
    keywords = None
    for k, v in sig.parameters.items():
        if v.kind == Parameter.VAR_POSITIONAL:
            varargs = k
        elif v.kind == Parameter.VAR_KEYWORD:
            keywords = k
    defaults = []
    for a in reversed(args):
        default = sig.parameters[a].default
        if default is _empty:
            break
        else:
            defaults.append(default)
    if defaults:
        defaults = tuple(reversed(defaults))
    else:
        defaults = None
    return FakeArgSpec(args, varargs, keywords, defaults)


if NO_ARGSPEC:
    getargspec = signature_argspec
    ArgSpec = FakeArgSpec
else:
    from inspect import getargspec, ArgSpec


importlib_invalidate_caches = getattr(
    importlib, u'invalidate_caches', lambda: ())
