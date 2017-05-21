#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Infer types of test function arguments using type annotations
"""

import hypothesis
import hypothesis.strategies as st
import inspect

__author__      = "Marco Sirabella"
__credits__     = ["Marco Sirabella"]  # Authors and bug reporters
__email__       = "msirabel@gmail.com"
__module__      = "Hypothesis"


type2strat = {}
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
def test(i: int):
    print(i)

test()
