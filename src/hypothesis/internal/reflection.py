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

"""This file can approximately be considered the collection of hypothesis going
to really unreasonable lengths to produce pretty output."""


from __future__ import division, print_function, absolute_import

import re
import ast
import uuid
import types
import hashlib
import inspect
from types import ModuleType
from functools import wraps

from hypothesis.configuration import storage_directory
from hypothesis.vendor.pretty import pretty
from hypothesis.internal.compat import ARG_NAME_ATTRIBUTE, hrange, \
    to_str, qualname, to_unicode, isidentifier, str_to_bytes, \
    getfullargspec, update_code_location


def fully_qualified_name(f):
    """Returns a unique identifier for f pointing to the module it was defined
    on, and an containing functions."""
    if f.__module__ is not None:
        return f.__module__ + '.' + qualname(f)
    else:
        return qualname(f)


def is_mock(obj):
    """Determine if the given argument is a mock type.

    We want to be able to detect these when dealing with various test
    args. As they are sneaky and can look like almost anything else,
    we'll check this by looking for random attributes.  This is more
    robust than looking for types.
    """
    for _ in range(10):
        if not hasattr(obj, str(uuid.uuid4())):
            return False
    return True


def function_digest(function):
    """Returns a string that is stable across multiple invocations across
    multiple processes and is prone to changing significantly in response to
    minor changes to the function.

    No guarantee of uniqueness though it usually will be.
    """
    hasher = hashlib.md5()
    try:
        hasher.update(to_unicode(inspect.getsource(function)).encode('utf-8'))
    # Different errors on different versions of python. What fun.
    except (OSError, IOError, TypeError):
        pass
    try:
        hasher.update(str_to_bytes(function.__name__))
    except AttributeError:
        pass
    try:
        hasher.update(function.__module__.__name__.encode('utf-8'))
    except AttributeError:
        pass
    try:
        hasher.update(str_to_bytes(repr(getfullargspec(function))))
    except TypeError:
        pass
    return hasher.digest()


def required_args(target, args=(), kwargs=()):
    """Return a set of names of required args to target that were not supplied
    in args or kwargs.

    This is used in builds() to determine which arguments to attempt to
    fill from type hints.  target may be any callable (including classes
    and bound methods).  args and kwargs should be as they are passed to
    builds() - that is, a tuple of values and a dict of names: values.
    """
    try:
        spec = getfullargspec(
            target.__init__ if inspect.isclass(target) else target)
    except TypeError:  # pragma: no cover
        return None
    # self appears in the argspec of __init__ and bound methods, but it's an
    # error to explicitly supply it - so we might skip the first argument.
    skip_self = int(inspect.isclass(target) or inspect.ismethod(target))
    # Start with the args that were not supplied and all kwonly arguments,
    # then remove all positional arguments with default values, and finally
    # remove kwonly defaults and any supplied keyword arguments
    return set(spec.args[skip_self + len(args):] + spec.kwonlyargs) \
        - set(spec.args[len(spec.args) - len(spec.defaults or ()):]) \
        - set(spec.kwonlydefaults or ()) - set(kwargs)


def convert_keyword_arguments(function, args, kwargs):
    """Returns a pair of a tuple and a dictionary which would be equivalent
    passed as positional and keyword args to the function. Unless function has.

    **kwargs the dictionary will always be empty.
    """
    argspec = getfullargspec(function)
    new_args = []
    kwargs = dict(kwargs)

    defaults = dict(argspec.kwonlydefaults or {})

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

    if kwargs and not argspec.varkw:
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

    new_args will only be non-empty if function has a variadic argument.
    """
    argspec = getfullargspec(function)
    new_kwargs = dict(argspec.kwonlydefaults or {})
    new_kwargs.update(kwargs)
    if not argspec.varkw:
        for k in new_kwargs.keys():
            if k not in argspec.args and k not in argspec.kwonlyargs:
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
    for kw in argspec.kwonlyargs:
        if kw not in new_kwargs:
            raise TypeError('No value provided for argument %s' % kw)

    if len(args) > len(argspec.args) and not argspec.varargs:
        raise TypeError(
            '%s() takes at most %d positional arguments (%d given)' % (
                function.__name__, len(argspec.args), len(args)
            )
        )

    for arg, name in zip(args, argspec.args):
        if name in new_kwargs:
            raise TypeError(
                '%s() got multiple values for keyword argument %r' % (
                    function.__name__, name
                ))
        else:
            new_kwargs[name] = arg
    return (
        tuple(args[len(argspec.args):]),
        new_kwargs,
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


LINE_CONTINUATION = re.compile(r"\\\n")
WHITESPACE = re.compile(r"\s+")
PROBABLY_A_COMMENT = re.compile("""#[^'"]*$""")
SPACE_FOLLOWS_OPEN_BRACKET = re.compile(r"\( ")
SPACE_PRECEDES_CLOSE_BRACKET = re.compile(r" \)")


def extract_lambda_source(f):
    """Extracts a single lambda expression from the string source. Returns a
    string indicating an unknown body if it gets confused in any way.

    This is not a good function and I am sorry for it. Forgive me my
    sins, oh lord
    """
    argspec = getfullargspec(f)
    arg_strings = []
    # In Python 2 you can have destructuring arguments to functions. This
    # results in an argspec with non-string values. I'm not very interested in
    # handling these properly, but it's important to not crash on them.
    bad_lambda = False
    for a in argspec.args:
        if isinstance(a, (tuple, list)):  # pragma: no cover
            arg_strings.append('(%s)' % (', '.join(a),))
            bad_lambda = True
        else:
            assert isinstance(a, str)
            arg_strings.append(a)
    if argspec.varargs:
        arg_strings.append('*' + argspec.varargs)
    elif argspec.kwonlyargs:
        arg_strings.append('*')
    for a in (argspec.kwonlyargs or []):
        default = (argspec.kwonlydefaults or {}).get(a)
        if default:
            arg_strings.append('{}={}'.format(a, default))
        else:
            arg_strings.append(a)

    if_confused = 'lambda %s: <unknown>' % (', '.join(arg_strings),)
    if bad_lambda:  # pragma: no cover
        return if_confused
    try:
        source = inspect.getsource(f)
    except IOError:
        return if_confused

    source = LINE_CONTINUATION.sub(' ', source)
    source = WHITESPACE.sub(' ', source)
    source = source.strip()
    assert 'lambda' in source

    tree = None

    try:
        tree = ast.parse(source)
    except SyntaxError:
        for i in hrange(len(source) - 1, len('lambda'), -1):
            prefix = source[:i]
            if 'lambda' not in prefix:
                break
            try:
                tree = ast.parse(prefix)
                source = prefix
                break
            except SyntaxError:
                continue
    if tree is None:
        if source.startswith('@'):
            # This will always eventually find a valid expression because
            # the decorator must be a valid Python function call, so will
            # eventually be syntactically valid and break out of the loop. Thus
            # this loop can never terminate normally, so a no branch pragma is
            # appropriate.
            for i in hrange(len(source) + 1):  # pragma: no branch
                p = source[1:i]
                if 'lambda' in p:
                    try:
                        tree = ast.parse(p)
                        source = p
                        break
                    except SyntaxError:
                        pass

    if tree is None:
        return if_confused

    all_lambdas = extract_all_lambdas(tree)
    aligned_lambdas = [
        l for l in all_lambdas
        if args_for_lambda_ast(l) == argspec.args
    ]
    if len(aligned_lambdas) != 1:
        return if_confused
    lambda_ast = aligned_lambdas[0]
    assert lambda_ast.lineno == 1
    source = source[lambda_ast.col_offset:].strip()

    source = source[source.index('lambda'):]
    for i in hrange(len(source), len('lambda'), -1):  # pragma: no branch
        try:
            parsed = ast.parse(source[:i])
            assert len(parsed.body) == 1
            assert parsed.body
            if isinstance(parsed.body[0].value, ast.Lambda):
                source = source[:i]
                break
        except SyntaxError:
            pass
    lines = source.split('\n')
    lines = [PROBABLY_A_COMMENT.sub('', l) for l in lines]
    source = '\n'.join(lines)

    source = WHITESPACE.sub(' ', source)
    source = SPACE_FOLLOWS_OPEN_BRACKET.sub('(', source)
    source = SPACE_PRECEDES_CLOSE_BRACKET.sub(')', source)
    source = source.strip()
    return source


def get_pretty_function_description(f):
    if not hasattr(f, '__name__'):
        return repr(f)
    name = f.__name__
    if name == '<lambda>':
        result = extract_lambda_source(f)
        return result
    elif isinstance(f, types.MethodType):
        self = f.__self__
        if not (self is None or inspect.isclass(self)):
            return '%r.%s' % (self, name)
    return name


def nicerepr(v):
    if inspect.isfunction(v):
        return get_pretty_function_description(v)
    elif isinstance(v, type):
        return v.__name__
    else:
        return to_str(pretty(v))


def arg_string(f, args, kwargs, reorder=True):
    if reorder:
        args, kwargs = convert_positional_arguments(f, args, kwargs)

    argspec = getfullargspec(f)

    bits = []

    for a in argspec.args:
        if a in kwargs:
            bits.append('%s=%s' % (a, nicerepr(kwargs.pop(a))))
    if kwargs:
        for a in sorted(kwargs):
            bits.append('%s=%s' % (a, nicerepr(kwargs[a])))

    return ', '.join([nicerepr(x) for x in args] + bits)


def unbind_method(f):
    """Take something that might be a method or a function and return the
    underlying function."""
    return getattr(f, 'im_func', getattr(f, '__func__', f))


def check_valid_identifier(identifier):
    if not isidentifier(identifier):
        raise ValueError('%r is not a valid python identifier' %
                         (identifier,))


def eval_directory():
    return storage_directory('eval_source')


eval_cache = {}


def source_exec_as_module(source):
    try:
        return eval_cache[source]
    except KeyError:
        pass

    result = ModuleType('hypothesis_temporary_module_%s' % (
        hashlib.sha1(str_to_bytes(source)).hexdigest(),
    ))
    assert isinstance(source, str)
    exec(source, result.__dict__)
    eval_cache[source] = result
    return result


COPY_ARGSPEC_SCRIPT = """
from hypothesis.utils.conventions import not_set

def accept(%(funcname)s):
    def %(name)s(%(argspec)s):
        return %(funcname)s(%(invocation)s)
    return %(name)s
""".strip() + '\n'


def define_function_signature(name, docstring, argspec):
    """A decorator which sets the name, argspec and docstring of the function
    passed into it."""
    check_valid_identifier(name)
    for a in argspec.args:
        check_valid_identifier(a)
    if argspec.varargs is not None:
        check_valid_identifier(argspec.varargs)
    if argspec.varkw is not None:
        check_valid_identifier(argspec.varkw)
    n_defaults = len(argspec.defaults or ())
    if n_defaults:
        parts = []
        for a in argspec.args[:-n_defaults]:
            parts.append(a)
        for a in argspec.args[-n_defaults:]:
            parts.append('%s=not_set' % (a,))
    else:
        parts = list(argspec.args)
    used_names = list(argspec.args) + list(argspec.kwonlyargs)
    used_names.append(name)

    for a in argspec.kwonlyargs:
        check_valid_identifier(a)

    def accept(f):
        fargspec = getfullargspec(f)
        must_pass_as_kwargs = []
        invocation_parts = []
        for a in argspec.args:
            if a not in fargspec.args and not fargspec.varargs:
                must_pass_as_kwargs.append(a)
            else:
                invocation_parts.append(a)
        if argspec.varargs:
            used_names.append(argspec.varargs)
            parts.append('*' + argspec.varargs)
            invocation_parts.append('*' + argspec.varargs)
        elif argspec.kwonlyargs:
            parts.append('*')
        for k in must_pass_as_kwargs:
            invocation_parts.append('%(k)s=%(k)s' % {'k': k})

        for k in argspec.kwonlyargs:
            invocation_parts.append('%(k)s=%(k)s' % {'k': k})
            if k in (argspec.kwonlydefaults or []):
                parts.append('%(k)s=not_set' % {'k': k})
            else:
                parts.append(k)
        if argspec.varkw:
            used_names.append(argspec.varkw)
            parts.append('**' + argspec.varkw)
            invocation_parts.append('**' + argspec.varkw)

        candidate_names = ['f'] + [
            'f_%d' % (i,) for i in hrange(1, len(used_names) + 2)
        ]

        for funcname in candidate_names:  # pragma: no branch
            if funcname not in used_names:
                break

        base_accept = source_exec_as_module(
            COPY_ARGSPEC_SCRIPT % {
                'name': name,
                'funcname': funcname,
                'argspec': ', '.join(parts),
                'invocation': ', '.join(invocation_parts)
            }).accept

        result = base_accept(f)
        result.__doc__ = docstring
        result.__defaults__ = argspec.defaults
        if argspec.kwonlydefaults:
            result.__kwdefaults__ = argspec.kwonlydefaults
        if argspec.annotations:
            result.__annotations__ = argspec.annotations
        return result
    return accept


def impersonate(target):
    """Decorator to update the attributes of a function so that to external
    introspectors it will appear to be the target function.

    Note that this updates the function in place, it doesn't return a
    new one.
    """
    def accept(f):
        f.__code__ = update_code_location(
            f.__code__,
            target.__code__.co_filename, target.__code__.co_firstlineno
        )
        f.__name__ = target.__name__
        f.__module__ = target.__module__
        f.__doc__ = target.__doc__
        return f
    return accept


def proxies(target):
    def accept(proxy):
        return impersonate(target)(wraps(target)(define_function_signature(
            target.__name__, target.__doc__, getfullargspec(target))(proxy)))
    return accept
