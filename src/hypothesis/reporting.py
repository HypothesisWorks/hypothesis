from __future__ import unicode_literals, print_function

from hypothesis.internal.dynamicvariables import DynamicVariable


def silent(value):
    pass


def default(value):
    print(value)


reporter = DynamicVariable(default)


def current_reporter():
    return reporter.value


def with_reporter(new_reporter):
    return reporter.with_value(new_reporter)
