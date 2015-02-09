# coding=utf-8

# Copyright (C) 2013-2015 David R. MacIver (david@drmaciver.com)

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

"""This file can approximately be considered the collection of hypothesis going
to really unreasonable lengths to produce pretty output."""

from __future__ import division, print_function, unicode_literals

import os
import re
import ast
import sys
import time
import types
import hashlib
import inspect
from functools import wraps

from hypothesis.conventions import not_set
from hypothesis.internal.compat import ARG_NAME_ATTRIBUTE, hrange
from hypothesis.internal.filestorage import storage_directory


def function_digest(function):
    """Returns a string that is stable across multiple invocations across
    multiple processes and is prone to changing significantly in response to
    minor changes to the function.

    No guarantee of uniqueness though it usually will be.

    """
    hasher = hashlib.md5()
    try:
        hasher.update(inspect.getsource(function).encode('utf-8'))
    # Different errors on different versions of python. What fun.
    except (OSError, IOError):
        pass
    hasher.update(function.__name__.encode('utf-8'))
    hasher.update(repr(inspect.getargspec(function)).encode('utf-8'))
    return hasher.digest()


def convert_keyword_arguments(function, args, kwargs):
    """Returns a pair of a tuple and a dictionary which would be equivalent
    passed as positional and keyword args to the function. Unless function has.

    **kwargs the dictionary will always be empty.

    """
    argspec = inspect.getargspec(function)
    new_args = []
    kwargs = dict(kwargs)

    defaults = {}

    if argspec.defaults:
        for name, value in zip(
                argspec.args[-len(argspec.defaults):],
                argspec.defaults
        ):
            defaults[name] = value

    n = max(len(args), len(argspec.args))

    for i in hrange(n):
        if i < len(args):
            new_args.append(args[i])
        else:
            arg_name = argspec.args[i]
            if arg_name in kwargs:
                new_args.append(kwargs.pop(arg_name))
            elif arg_name in defaults:
                new_args.append(defaults[arg_name])
            else:
                raise TypeError('No value provided for argument %r' % (
                    arg_name
                ))

    if kwargs and not argspec.keywords:
        if len(kwargs) > 1:
            raise TypeError('%s() got unexpected keyword arguments %s' % (
                function.__name__, ', '.join(map(repr, kwargs))
            ))
        else:
            bad_kwarg = next(iter(kwargs))
            raise TypeError('%s() got an unexpected keyword argument %r' % (
                function.__name__, bad_kwarg
            ))
    return tuple(new_args), kwargs


def convert_positional_arguments(function, args, kwargs):
    """Return a tuple (new_args, new_kwargs) where all possible arguments have
    been moved to kwargs.

    new_args will only be non-empty if function has a
    variadic argument.

    """
    argspec = inspect.getargspec(function)
    kwargs = dict(kwargs)
    if not argspec.keywords:
        for k in kwargs.keys():
            if k not in argspec.args:
                raise TypeError(
                    '%s() got an unexpected keyword argument %r' % (
                        function.__name__, k
                    ))
    if len(args) < len(argspec.args):
        for i in hrange(
            len(args), len(argspec.args) - len(argspec.defaults or ())
        ):
            if argspec.args[i] not in kwargs:
                raise TypeError('No value provided for argument %s' % (
                    argspec.args[i],
                ))

    if len(args) > len(argspec.args) and not argspec.varargs:
        raise TypeError(
            '%s() takes at most %d positional arguments (%d given)' % (
                function.__name__, len(argspec.args), len(args)
            )
        )

    for arg, name in zip(args, argspec.args):
        if name in kwargs:
            raise TypeError(
                '%s() got multiple values for keyword argument %r' % (
                    function.__name__, name
                ))
        else:
            kwargs[name] = arg
    return (
        tuple(args[len(argspec.args):]),
        kwargs,
    )


def extract_all_lambdas(tree):
    lambdas = []

    class Visitor(ast.NodeVisitor):

        def visit_Lambda(self, node):
            lambdas.append(node)

    Visitor().visit(tree)

    return lambdas


def args_for_lambda_ast(l):
    return [getattr(n, ARG_NAME_ATTRIBUTE) for n in l.args.args]


def find_offset(string, line, column):
    current_line = 1
    current_line_offset = 0
    while current_line < line:
        current_line_offset = string.index('\n', current_line_offset + 1)
        current_line += 1
    return current_line_offset + column


WHITESPACE = re.compile(r"\s+")
PROBABLY_A_COMMENT = re.compile("""#[^'"]*$""")


def extract_lambda_source(f):
    """Extracts a single lambda expression from the string source. Returns a
    string indicating an unknown body if it gets confused in any way.

    This is not a good function and I am sorry for it. Forgive me my
    sins, oh lord

    """
    args = inspect.getargspec(f).args
    if_confused = 'lambda %s: <unknown>' % (', '.join(args),)
    try:
        source = inspect.getsource(f)
    except IOError:
        return if_confused

    try:
        try:
            tree = ast.parse(source)
        except IndentationError:
            source = 'with 0:\n' + source
            tree = ast.parse(source)
    except SyntaxError:
        return if_confused

    all_lambdas = extract_all_lambdas(tree)
    aligned_lambdas = [
        l for l in all_lambdas
        if args_for_lambda_ast(l) == args
    ]
    if len(aligned_lambdas) != 1:
        return if_confused
    lambda_ast = aligned_lambdas[0]
    line_start = lambda_ast.lineno
    column_offset = lambda_ast.col_offset
    source = source[find_offset(source, line_start, column_offset):].strip()

    source = source[source.index('lambda'):]

    for i in hrange(len(source), -1, -1):  # pragma: no branch
        try:
            parsed = ast.parse(source[:i])
            assert len(parsed.body) == 1
            assert parsed.body
            if not isinstance(parsed.body[0].value, ast.Lambda):
                continue
            source = source[:i]
            break
        except SyntaxError:
            pass
    lines = source.split('\n')
    lines = [PROBABLY_A_COMMENT.sub('', l) for l in lines]
    source = '\n'.join(lines)

    source = WHITESPACE.sub(' ', source)
    source = source.strip()
    return source


def get_pretty_function_description(f):
    name = f.__name__
    if name == '<lambda>':
        result = extract_lambda_source(f)
        return result
    elif isinstance(f, types.MethodType):
        self = f.__self__
        if not (self is None or inspect.isclass(self)):
            return '%r.%s' % (self, name)
    return name


def arg_string(f, args, kwargs):
    args, kwargs = convert_positional_arguments(f, args, kwargs)

    argspec = inspect.getargspec(f)

    bits = []

    for a in argspec.args:
        if a in kwargs:
            bits.append('%s=%r' % (a, kwargs.pop(a)))
    if kwargs:
        for a in sorted(kwargs):
            bits.append('%s=%r' % (a, kwargs[a]))

    return ', '.join(
        [repr(x) for x in args] +
        bits
    )


def unbind_method(f):
    """Take something that might be a method or a function and return the
    underlying function."""
    return getattr(f, 'im_func', getattr(f, '__func__', f))


VALID_PYTHON_IDENTIFIER = re.compile(
    r"^[a-zA-Z_][a-zA-Z0-9_]*$"
)


def check_valid_identifier(identifier):
    if not VALID_PYTHON_IDENTIFIER.match(identifier):
        raise ValueError('%r is not a valid python identifier' % (identifier,))


def eval_directory():
    return storage_directory('eval_source')


def add_directory_to_path(d):
    if d not in sys.path:
        sys.path.insert(0, d)


eval_cache = {}


def source_exec_as_module(source):
    try:
        return eval_cache[source]
    except KeyError:
        pass

    d = eval_directory()
    add_directory_to_path(d)
    # Try writing the source to a series of files. If we get an import error
    # importing after writing we're experiencing a race condition in the
    # import mechanism. Try again a few times. If after a 1.5 second wait it's
    # still not working something else is going on.
    # See http://bugs.python.org/issue23412
    waits = [0.0, 0.001, 0.01, 0.1, 0.5, 1.0, 1.5]
    for i, wait in enumerate(waits):  # pragma: no branch
        name = 'hypothesis_temporary_module_%s_%d' % (
            hashlib.sha1(source.encode('utf-8')).hexdigest(),
            i,
        )
        filepath = os.path.join(d, name + '.py')
        f = open(filepath, 'w')
        f.write(source)
        f.close()
        assert os.path.exists(filepath)
        assert open(filepath).read() == source
        time.sleep(wait)
        try:
            result = __import__(name)
            eval_cache[source] = result
            return result
        except ImportError:  # pragma: no cover
            if wait == waits[-1]:
                raise

COPY_ARGSPEC_SCRIPT = """
from hypothesis.conventions import not_set

def accept(f):
    def %(name)s(%(argspec)s):
        return f(%(invocation)s)
    return %(name)s
""".strip() + '\n'


def copy_argspec(name, argspec):
    """A decorator which sets the name and argspec of the function passed into
    it."""
    check_valid_identifier(name)
    for a in argspec.args:
        check_valid_identifier(a)
    if argspec.varargs is not None:
        check_valid_identifier(argspec.varargs)
    if argspec.keywords is not None:
        check_valid_identifier(argspec.keywords)
    n_defaults = len(argspec.defaults or ())
    invocation_parts = []
    if n_defaults:
        parts = []
        for a in argspec.args[:-n_defaults]:
            parts.append(a)
        for a in argspec.args[-n_defaults:]:
            parts.append('%s=not_set' % (a,))
    else:
        parts = list(argspec.args)

    invocation_parts = []
    if argspec.varargs:
        parts.append('*' + argspec.varargs)
        invocation_parts.append('*' + argspec.varargs)

    for a in argspec.args:
        invocation_parts.append('%s=%s' % (a, a))

    if argspec.keywords:
        parts.append('**' + argspec.keywords)
        invocation_parts.append('**' + argspec.keywords)

    accept_with_right_args = source_exec_as_module(
        COPY_ARGSPEC_SCRIPT % {
            'name': name,
            'argspec': ', '.join(parts),
            'invocation': ', '.join(invocation_parts)
        }).accept
    defaults = {}
    for name, default in zip(
        argspec.args[-n_defaults:], argspec.defaults or ()
    ):
        defaults[name] = default

    def accept(f):
        def convert_arguments(*args, **kwargs):
            for k, v in kwargs.items():
                if v is not_set:
                    kwargs[k] = defaults[k]
            return f(*args, **kwargs)
        return accept_with_right_args(convert_arguments)
    return accept


def proxies(target):
    def accept(proxy):
        return wraps(target)(
            copy_argspec(target.__name__, inspect.getargspec(target))(proxy))
    return accept
