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
    def __init__(self):
        for strat_name in dir(st):  # Iterate through all attributes in module
            strat = getattr(st, strat_name)  # get attribute of name
            del strat_name  # No need for the strategy name anymore,
            if inspect.isfunction(strat):  # If attribute is callable function
                try:
                    strat = strat()  # Call wrapping function
                    if isinstance(
                            strat,  # If it is a search strategy
                            hypothesis.searchstrategy.strategies.SearchStrategy
                    ):
                        self.append(strat)  # Add strategy to self
                except (TypeError, hypothesis.errors.NoExamples):
                    # If not enough args or not able to get examples
                    pass

    def __getitem__(self, item):
        if isinstance(item, typing._Union):  # If is union of multiple types
            both = item.__args__  # assign each item of args to both
            return self[both[0]] | self[both[1]]  # Call __getitem__ for each
        return super().__getitem__(item)  # If not union just return normally

    def append(self, strategy):
        """
        Add strategy and respective type as key
        """
        self[type(strategy.example())] = strategy


type2strat = Type2Strat()


def infer(func):
    """
    a decorator for turning a test function that accepts argument into a
    randomized test

    This is a offshoot of the given function, rather than accept arguments of
    what strategies the tests should use, tries to infer based on type
    annotations of wrapped function
    """

    types = func.__annotations__
    kwargs = {}
    for key, value in types.items():
        kwargs[key] = type2strat[value]
    func = hypothesis.given(**kwargs)(func)
    return func
