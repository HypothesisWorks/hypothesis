# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Most of this work is copyright (C) 2013-2020 David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
# CONTRIBUTING.rst for a full list of people who may hold copyright, and
# consult the git log if you need to determine who owns an individual
# contribution.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.
#
# END HEADER

import codecs
import importlib
import inspect
import platform
import sys
import time
import typing

PYPY = platform.python_implementation() == "PyPy"
CAN_PACK_HALF_FLOAT = sys.version_info[:2] >= (3, 6)
WINDOWS = platform.system() == "Windows"


def bit_length(n):
    return n.bit_length()


def str_to_bytes(s):
    return s.encode(a_good_encoding())


def escape_unicode_characters(s):
    return codecs.encode(s, "unicode_escape").decode("ascii")


def int_from_bytes(data):
    return int.from_bytes(data, "big")


def int_to_bytes(i, size):
    return i.to_bytes(size, "big")


def int_to_byte(i):
    return bytes([i])


def benchmark_time():
    return time.monotonic()


def a_good_encoding():
    return "utf-8"


def to_unicode(x):
    if isinstance(x, str):
        return x
    else:
        return x.decode(a_good_encoding())


def qualname(f):
    try:
        return f.__qualname__
    except AttributeError:
        return f.__name__


try:
    # These types are new in Python 3.7, but also (partially) backported to the
    # typing backport on PyPI.  Use if possible; or fall back to older names.
    typing_root_type = (typing._Final, typing._GenericAlias)  # type: ignore
    ForwardRef = typing.ForwardRef  # type: ignore
except AttributeError:
    typing_root_type = (typing.TypingMeta, typing.TypeVar)  # type: ignore
    try:
        typing_root_type += (typing._Union,)  # type: ignore
    except AttributeError:
        pass
    ForwardRef = typing._ForwardRef  # type: ignore


def is_typed_named_tuple(cls):
    """Return True if cls is probably a subtype of `typing.NamedTuple`.

    Unfortunately types created with `class T(NamedTuple):` actually
    subclass `tuple` directly rather than NamedTuple.  This is annoying,
    and means we just have to hope that nobody defines a different tuple
    subclass with similar attributes.
    """
    return (
        issubclass(cls, tuple)
        and hasattr(cls, "_fields")
        and hasattr(cls, "_field_types")
    )


if sys.version_info[:2] < (3, 6):
    # When we drop support for Python 3.5, `get_type_hints` and
    # `is_typed_named_tuple` should be moved to reflection.py

    def get_type_hints(thing):
        if inspect.isclass(thing) and not hasattr(thing, "__signature__"):
            if is_typed_named_tuple(thing):
                # Special handling for typing.NamedTuple
                return thing._field_types  # type: ignore
            thing = thing.__init__  # type: ignore
        try:
            spec = inspect.getfullargspec(thing)
            return {
                k: v
                for k, v in spec.annotations.items()
                if k in (spec.args + spec.kwonlyargs) and isinstance(v, type)
            }
        except TypeError:
            return {}


else:

    def get_type_hints(thing):
        if inspect.isclass(thing) and not hasattr(thing, "__signature__"):
            if is_typed_named_tuple(thing):
                # Special handling for typing.NamedTuple
                return thing._field_types  # type: ignore
            thing = thing.__init__  # type: ignore
        try:
            return typing.get_type_hints(thing)
        except TypeError:
            return {}


importlib_invalidate_caches = getattr(importlib, "invalidate_caches", lambda: ())


def update_code_location(code, newfile, newlineno):
    """Take a code object and lie shamelessly about where it comes from.

    Why do we want to do this? It's for really shallow reasons involving
    hiding the hypothesis_temporary_module code from test runners like
    pytest's verbose mode. This is a vastly disproportionate terrible
    hack that I've done purely for vanity, and if you're reading this
    code you're probably here because it's broken something and now
    you're angry at me. Sorry.
    """
    if hasattr(code, "replace"):
        # Python 3.8 added positional-only params (PEP 570), and thus changed
        # the layout of code objects.  In beta1, the `.replace()` method was
        # added to facilitate future-proof code.  See BPO-37032 for details.
        return code.replace(co_filename=newfile, co_firstlineno=newlineno)

    # This field order is accurate for 3.5 - 3.7, but not 3.8 when a new field
    # was added for positional-only arguments.  However it also added a .replace()
    # method that we use instead of field indices, so they're fine as-is.
    CODE_FIELD_ORDER = [
        "co_argcount",
        "co_kwonlyargcount",
        "co_nlocals",
        "co_stacksize",
        "co_flags",
        "co_code",
        "co_consts",
        "co_names",
        "co_varnames",
        "co_filename",
        "co_name",
        "co_firstlineno",
        "co_lnotab",
        "co_freevars",
        "co_cellvars",
    ]
    unpacked = [getattr(code, name) for name in CODE_FIELD_ORDER]
    unpacked[CODE_FIELD_ORDER.index("co_filename")] = newfile
    unpacked[CODE_FIELD_ORDER.index("co_firstlineno")] = newlineno
    return type(code)(*unpacked)


def cast_unicode(s, encoding=None):
    if isinstance(s, bytes):
        return s.decode(encoding or a_good_encoding(), "replace")
    return s


def get_stream_enc(stream, default=None):
    return getattr(stream, "encoding", None) or default


# Under Python 2, math.floor and math.ceil return floats, which cannot
# represent large integers - eg `float(2**53) == float(2**53 + 1)`.
# We therefore implement them entirely in (long) integer operations.
# We use the same trick on Python 3, because Numpy values and other
# custom __floor__ or __ceil__ methods may convert via floats.
# See issue #1667, Numpy issue 9068.
def floor(x):
    y = int(x)
    if y != x and x < 0:
        return y - 1
    return y


def ceil(x):
    y = int(x)
    if y != x and x > 0:
        return y + 1
    return y


try:
    from django.test import TransactionTestCase

    def bad_django_TestCase(runner):
        if runner is None:
            return False
        if not isinstance(runner, TransactionTestCase):
            return False

        from hypothesis.extra.django._impl import HypothesisTestCase

        return not isinstance(runner, HypothesisTestCase)


except Exception:
    # Can't use ImportError, because of e.g. Django config errors
    def bad_django_TestCase(runner):
        return False
