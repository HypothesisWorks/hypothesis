from hypothesis.internal.utils.reflection import source_exec_as_module


def test_can_eval_as_source():
    assert source_exec_as_module('foo=1').foo == 1


def test_caches():
    x = source_exec_as_module('foo=2')
    y = source_exec_as_module('foo=2')
    assert x is y


RECURSIVE = """
from hypothesis.internal.utils.reflection import source_exec_as_module

def test_recurse():
    assert not (
        source_exec_as_module("too_much_recursion = False").too_much_recursion)
"""


def test_can_call_self_recursively():
    source_exec_as_module(RECURSIVE).test_recurse()
