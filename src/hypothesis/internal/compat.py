# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2015 David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
# CONTRIBUTING.rst for a full list of people who may hold copyright, and
# consult the git log if you need to determine who owns an individual
# contribution.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.
#
# END HEADER

# pylint: skip-file

from __future__ import division, print_function, absolute_import

import os
import re
import sys
import math
import codecs
import platform
import importlib
from decimal import Context, Decimal, Inexact
from collections import namedtuple

try:
    from collections import OrderedDict, Counter
except ImportError:  # pragma: no cover
    from ordereddict import OrderedDict
    from counter import Counter


PY2 = sys.version_info[0] == 2
PY3 = sys.version_info[0] == 3
PYPY = platform.python_implementation() == 'PyPy'
PY26 = sys.version_info[:2] == (2, 6)
NO_ARGSPEC = sys.version_info[:2] >= (3, 5)
HAS_SIGNATURE = sys.version_info[:2] >= (3, 3)
CAN_UNPACK_BYTE_ARRAY = sys.version_info[:3] >= (2, 7, 4)

WINDOWS = platform.system() == 'Windows'

if PY26:
    from hypothesis import __version__ as thisversion
    try:
        from hypothesislegacysupport import __version__ as thatversion
    except ImportError:
        raise ImportError(
            'Hypothesis is not supported on Python 2.6 without the '
            'hypothesislegacysupport installed. Check that you have a '
            'license to use it and then install it in order to continue.'
        )
    if thisversion != thatversion:
        raise ImportError((
            'hypothesis and hypothesislegacysupport must have exactly the '
            'same version, but you have hypothesis==%s installed and '
            'hypothesislegacysupport==%s installed. Please replace one '
            'with a version compatible with the other.'
        ) % (thisversion, thatversion))

    from hypothesislegacysupport import GzipFile, bit_length, sha1, \
        b64encode, b64decode

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
    from gzip import GzipFile
    from hashlib import sha1
    from base64 import b64encode, b64decode

    def bit_length(n):
        return n.bit_length()

    def float_to_decimal(f):
        return Decimal(f)


if PY3:
    def str_to_bytes(s):
        return s.encode(a_good_encoding())

    def int_to_text(i):
        return str(i)

    text_type = str
    binary_type = bytes
    hrange = range
    ARG_NAME_ATTRIBUTE = 'arg'
    integer_types = (int,)
    hunichr = chr
    from functools import reduce

    def unicode_safe_repr(x):
        return repr(x)

    def isidentifier(s):
        return s.isidentifier()

    def escape_unicode_characters(s):
        return codecs.encode(s, 'unicode_escape').decode('ascii')

    def print_unicode(x):
        print(x)

    exec("""
def quiet_raise(exc):
    raise exc from None
""")

    def int_from_bytes(data):
        return int.from_bytes(data, 'big')

    def int_to_bytes(i, size):
        return i.to_bytes(size, 'big')

    def bytes_from_list(ls):
        return bytes(ls)

    def to_bytes_sequence(ls):
        return bytes(ls)

    def zero_byte_sequence(n):
        return bytes(n)
else:
    import struct

    def zero_byte_sequence(n):
        return b'\0' * n

    def int_from_bytes(data):
        assert isinstance(data, bytearray)
        if CAN_UNPACK_BYTE_ARRAY:
            unpackable_data = data
        else:
            unpackable_data = bytes(data)
        result = 0
        i = 0
        while i + 4 <= len(data):
            result <<= 32
            result |= struct.unpack('>I', unpackable_data[i:i + 4])[0]
            i += 4
        while i < len(data):
            result <<= 8
            result |= data[i]
            i += 1
        return int(result)

    def int_to_bytes(i, size):
        assert i >= 0
        result = bytearray(size)
        j = size - 1
        while i and j >= 0:
            result[j] = i & 255
            i >>= 8
            j -= 1
        if i:
            raise OverflowError('int too big to convert')
        return hbytes(result)

    def bytes_from_list(ls):
        return bytes(bytearray(ls))

    def to_bytes_sequence(ls):
        return bytearray(ls)

    def str_to_bytes(s):
        return s

    def int_to_text(i):
        return str(i).decode('ascii')

    VALID_PYTHON_IDENTIFIER = re.compile(
        r"^[a-zA-Z_][a-zA-Z0-9_]*$"
    )

    def isidentifier(s):
        return VALID_PYTHON_IDENTIFIER.match(s)

    def unicode_safe_repr(x):
        r = repr(x)
        assert isinstance(r, str)
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

    ARG_NAME_ATTRIBUTE = 'id'
    integer_types = (int, long)
    hunichr = unichr
    reduce = reduce

    def escape_unicode_characters(s):
        return codecs.encode(s, 'string_escape')

    def print_unicode(x):
        if isinstance(x, unicode):
            x = x.encode(a_good_encoding())
        print(x)

    def quiet_raise(exc):
        raise exc


def a_good_encoding():
    return 'utf-8'


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
        return f.im_class.__name__ + '.' + f.__name__
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
    importlib, 'invalidate_caches', lambda: ())


if PY2:
    CODE_FIELD_ORDER = [
        'co_argcount',
        'co_nlocals',
        'co_stacksize',
        'co_flags',
        'co_code',
        'co_consts',
        'co_names',
        'co_varnames',
        'co_filename',
        'co_name',
        'co_firstlineno',
        'co_lnotab',
        'co_freevars',
        'co_cellvars',
    ]
else:
    CODE_FIELD_ORDER = [
        'co_argcount',
        'co_kwonlyargcount',
        'co_nlocals',
        'co_stacksize',
        'co_flags',
        'co_code',
        'co_consts',
        'co_names',
        'co_varnames',
        'co_filename',
        'co_name',
        'co_firstlineno',
        'co_lnotab',
        'co_freevars',
        'co_cellvars',
    ]


def update_code_location(code, newfile, newlineno):
    """Take a code object and lie shamelessly about where it comes from.

    Why do we want to do this? It's for really shallow reasons involving
    hiding the hypothesis_temporary_module code from test runners like
    py.test's verbose mode. This is a vastly disproportionate terrible
    hack that I've done purely for vanity, and if you're reading this
    code you're probably here because it's broken something and now
    you're angry at me. Sorry.

    """
    unpacked = [
        getattr(code, name) for name in CODE_FIELD_ORDER
    ]
    unpacked[CODE_FIELD_ORDER.index('co_filename')] = newfile
    unpacked[CODE_FIELD_ORDER.index('co_firstlineno')] = newlineno
    return type(code)(*unpacked)


class compatbytes(bytearray):
    __name__ = 'bytes'

    def __init__(self, *args, **kwargs):
        bytearray.__init__(self, *args, **kwargs)
        self.__hash = None

    def __str__(self):
        return bytearray.__str__(self)

    def __repr__(self):
        return 'compatbytes(b%r)' % (str(self),)

    def __hash__(self):
        if self.__hash is None:
            self.__hash = hash(str(self))
        return self.__hash

    def count(self, value):
        c = 0
        for w in self:
            if w == value:
                c += 1
        return c

    def index(self, value):
        for i, v in enumerate(self):
            if v == value:
                return i
        raise ValueError('Value %r not in sequence %r' % (value, self))

    def __add__(self, value):
        return compatbytes(bytearray.__add__(self, value))

    def __radd__(self, value):
        return compatbytes(bytearray.__radd__(self, value))

    def __mul__(self, value):
        return compatbytes(bytearray.__mul__(self, value))

    def __rmul__(self, value):
        return compatbytes(bytearray.__rmul__(self, value))

    def __getitem__(self, *args, **kwargs):
        r = bytearray.__getitem__(self, *args, **kwargs)
        if isinstance(r, bytearray):
            return compatbytes(r)
        else:
            return r

    __setitem__ = None

    def join(self, parts):
        result = bytearray()
        first = True
        for p in parts:
            if not first:
                result.extend(self)
            first = False
            result.extend(p)
        return compatbytes(result)

    def __contains__(self, value):
        return any(v == value for v in self)

if PY2:
    hbytes = compatbytes
    reasonable_byte_type = bytearray
    string_types = (str, unicode)
else:
    hbytes = bytes
    reasonable_byte_type = bytes
    string_types = (str,)


if PY2:
    def to_str(s):
        if isinstance(s, unicode):
            return s.encode(a_good_encoding())
        assert isinstance(s, str)
        return s
else:
    def to_str(s):
        return s


def cast_unicode(s, encoding=None):
    if isinstance(s, bytes):
        return s.decode(encoding or a_good_encoding(), 'replace')
    return s


def get_stream_enc(stream, default=None):
    return getattr(stream, 'encoding', None) or default
