# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2018 David R. MacIver
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

import re
import sys
import math
import time
import array
import codecs
import platform
import importlib
from base64 import b64encode
from collections import namedtuple

try:
    from collections import OrderedDict, Counter
except ImportError:  # pragma: no cover
    from ordereddict import OrderedDict
    from counter import Counter


PY2 = sys.version_info[0] == 2
PY3 = sys.version_info[0] == 3
PYPY = platform.python_implementation() == 'PyPy'
CAN_UNPACK_BYTE_ARRAY = sys.version_info[:3] >= (2, 7, 4)

WINDOWS = platform.system() == 'Windows'

if sys.version_info[:2] <= (2, 6):
    raise ImportError(
        'Hypothesis is not supported on Python versions before 2.7'
    )


def bit_length(n):
    return n.bit_length()


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

    def to_bytes_sequence(ls):
        return bytes(ls)

    def int_to_byte(i):
        return bytes([i])

    import struct

    struct_pack = struct.pack
    struct_unpack = struct.unpack

    def benchmark_time():
        return time.monotonic()
else:
    import struct

    def struct_pack(*args):
        return hbytes(struct.pack(*args))

    if CAN_UNPACK_BYTE_ARRAY:
        def struct_unpack(fmt, string):
            return struct.unpack(fmt, string)
    else:
        def struct_unpack(fmt, string):
            return struct.unpack(fmt, str(string))

    def int_from_bytes(data):
        if CAN_UNPACK_BYTE_ARRAY:
            unpackable_data = data
        elif isinstance(data, bytearray):
            unpackable_data = bytes(data)
        else:
            unpackable_data = data
        assert isinstance(data, (bytes, bytearray))
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

    int_to_byte = chr

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

    def escape_unicode_characters(s):
        return codecs.encode(s, 'string_escape')

    def print_unicode(x):
        if isinstance(x, unicode):
            x = x.encode(a_good_encoding())
        print(x)

    def quiet_raise(exc):
        raise exc

    def benchmark_time():
        return time.time()


# coverage mixes unicode and str filepaths on Python 2, which causes us
# problems if we're running under unicodenazi (it might also cause problems
# when not running under unicodenazi, but hard to say for sure). This method
# exists to work around that: If we're given a unicode filepath, we turn it
# into a string file path using the appropriate encoding. See
# https://bitbucket.org/ned/coveragepy/issues/602/ for more information.
if PY2:
    def encoded_filepath(filepath):
        if isinstance(filepath, text_type):
            return filepath.encode(sys.getfilesystemencoding())
        else:
            return filepath
else:
    def encoded_filepath(filepath):
        return filepath


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


if PY2:
    FullArgSpec = namedtuple('FullArgSpec', 'args, varargs, varkw, defaults, '
                             'kwonlyargs, kwonlydefaults, annotations')

    def getfullargspec(func):
        import inspect
        args, varargs, varkw, defaults = inspect.getargspec(func)
        return FullArgSpec(args, varargs, varkw, defaults, [], None,
                           getattr(func, '__annotations__', {}))
else:
    from inspect import getfullargspec, FullArgSpec


if sys.version_info[:2] < (3, 6):
    def get_type_hints(thing):
        try:
            spec = getfullargspec(thing)
            return {
                k: v for k, v in spec.annotations.items()
                if k in (spec.args + spec.kwonlyargs) and isinstance(v, type)
            }
        except TypeError:
            return {}
else:
    def get_type_hints(thing):
        try:
            import typing
            return typing.get_type_hints(thing)
        except TypeError:
            return {}


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
        assert isinstance(value, compatbytes)
        return compatbytes(bytearray.__add__(self, value))

    def __radd__(self, value):
        assert isinstance(value, compatbytes)
        return compatbytes(bytearray.__add__(value, self))

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


EMPTY_BYTES = hbytes(b'')

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


def implements_iterator(it):
    """Turn things with a __next__ attribute into iterators on Python 2."""
    if PY2 and not hasattr(it, 'next') and hasattr(it, '__next__'):
        it.next = it.__next__
    return it


if PY3:
    FileNotFoundError = FileNotFoundError
else:
    FileNotFoundError = IOError

# We need to know what sort of exception gets thrown when you try to write over
# an existing file where you're not allowed to. This is rather less consistent
# between versions than might be hoped.
if PY3:
    FileExistsError = FileExistsError

elif WINDOWS:
    FileExistsError = WindowsError

else:
    # This doesn't happen in this case: We're not on windows and don't support
    # the x flag because it's Python 2, so there are no places where this can
    # be thrown.
    FileExistsError = None


if PY2:
    # Under Python 2, math.floor and math.ceil return floats, which cannot
    # represent large integers - eg `float(2**53) == float(2**53 + 1)`.
    # We therefore implement them entirely in (long) integer operations.
    def floor(x):
        if int(x) != x and x < 0:
            return int(x) - 1
        return int(x)

    def ceil(x):
        if int(x) != x and x > 0:
            return int(x) + 1
        return int(x)
else:
    floor = math.floor
    ceil = math.ceil


try:
    from math import gcd
except ImportError:
    from fractions import gcd


if PY2:
    def b64decode(s):
        from base64 import b64decode as base
        return hbytes(base(s))
else:
    from base64 import b64decode
