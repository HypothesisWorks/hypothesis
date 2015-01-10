"""
This file can approximately be considered the collection of hypothesis going to
really unreasonable lengths to produce pretty output.
"""

import inspect
from six.moves import xrange
import types
import ast
import re


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


def extract_all_lambdas(tree):
    lambdas = []

    class Visitor(ast.NodeVisitor):
        def visit_Lambda(self, node):
            lambdas.append(node)

    Visitor().visit(tree)

    return lambdas


def args_for_lambda_ast(l):
    return [n.id for n in l.args.args]


def find_offset(string, line, column):
    if line < 1:
        raise ValueError("Line out of range: %d < 1" % (line,))
    current_line = 1
    current_line_offset = 0
    while current_line < line:
        current_line_offset = string.index("\n", current_line_offset+1)
        current_line += 1
    return current_line_offset + column


WHITESPACE = re.compile('\s+')


def extract_lambda_source(f):
    """
    Extracts a single lambda expression from the string source. Returns a
    string indicating an unknown body if it gets confused in any way.

    This is not a good function and I am sorry for it. Forgive me my sins, oh
    lord
    """
    args = inspect.getargspec(f).args
    if_confused = "lambda %s: <unknown>" % (', '.join(args),)
    try:
        source = inspect.getsource(f)
    except IOError:
        return if_confused

    try:
        tree = ast.parse(source)
    except IndentationError:
        source = "with 0:\n" + source
        tree = ast.parse(source)

    all_lambdas = extract_all_lambdas(tree)
    aligned_lambdas = [
        l for l in all_lambdas
        if args_for_lambda_ast
    ]
    if len(aligned_lambdas) != 1:
        return if_confused
    lambda_ast = aligned_lambdas[0]
    line_start = lambda_ast.lineno
    column_offset = lambda_ast.col_offset
    source = source[find_offset(source, line_start, column_offset):].strip()

    source = source[source.index("lambda"):]

    for i in xrange(len(source), -1, -1):
        try:
            ast.parse(source[:i])
            source = source[:i]
            break
        except SyntaxError:
            pass
    source = WHITESPACE.sub(source, " ")
    source = source.strip()
    if source[0] == '(' and source[-1] == ')':
        source = source[1:-1]
    return source


def get_pretty_function_description(f):
    name = f.__name__
    if name == '<lambda>':
        return extract_lambda_source(f)
    elif isinstance(f, types.MethodType):
        self = f.im_self
        if self is None:
            return "%s.%s" % (f.im_class.__name__, name)
        elif inspect.isclass(self):
            return "%s.%s" % (self.__name__, name)
        else:
            return "%r.%s" % (self, name)
    else:
        return name
