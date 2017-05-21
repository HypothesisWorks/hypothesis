#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Infer types of test function arguments using type annotations
"""

import hypothesis
import hypothesis.strategies as st
import inspect
import typing

__author__      = "Marco Sirabella"
__credits__     = ["Marco Sirabella"]  # Authors and bug reporters
__email__       = "msirabel@gmail.com"
__module__      = "Hypothesis"


class Type2Strat(dict):
    def __getitem__(self, item):
        if isinstance(item, typing._Union):
            both = item.__args__
            return self[both[0]] | self[both[1]]
        return super().__getitem__(item)

type2strat = Type2Strat()
for strat_name in dir(st):
    strat = getattr(st, strat_name)
    del strat_name
    if inspect.isfunction(strat):
        try:
            strat = strat()
            if isinstance(
                    strat,
                    hypothesis.searchstrategy.strategies.SearchStrategy
                    ):
                type2strat[type(strat.example())] = strat
        except (TypeError, hypothesis.errors.NoExamples):
            pass


def infer(func):
    types = func.__annotations__
    kwargs = {}
    for key, value in types.items():
        kwargs[key] = type2strat[value]
    func = hypothesis.given(**kwargs)(func)
    return func


# Testing quickly

@infer
def test_int(i: int):
    assert abs(i) >= 0

@infer
def oneorother(i: typing.Union[int, float]):
    if isinstance(i, int):
        assert type(i) == int
    else:
        assert isinstance(i, float)

test_int()
oneorother()
