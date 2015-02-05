from __future__ import unicode_literals, print_function

from hypothesis.internal.dynamicvariables import DynamicVariable


def silent(value):
    pass


reporter = DynamicVariable(print)


def current_reporter():
    return reporter.value


def with_reporter(new_reporter):
    return reporter.with_value(new_reporter)
