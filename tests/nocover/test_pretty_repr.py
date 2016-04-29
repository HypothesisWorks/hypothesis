# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2015 David R. MacIver
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

from __future__ import division, print_function, absolute_import

import hypothesis.strategies as st
from hypothesis import given, settings
from hypothesis.errors import InvalidArgument
from hypothesis.control import reject
from hypothesis.internal.compat import OrderedDict


def foo(x):
    pass


def bar(x):
    pass


def baz(x):
    pass


fns = [
    foo, bar, baz
]


def return_args(*args, **kwargs):
    return args, kwargs


def builds_ignoring_invalid(target, *args, **kwargs):
    def splat(value):
        try:
            result = target(*value[0], **value[1])
            result.validate()
            return result
        except InvalidArgument:
            reject()
    return st.tuples(
        st.tuples(*args), st.fixed_dictionaries(kwargs)).map(splat)


size_strategies = dict(
    min_size=st.integers(min_value=0, max_value=100) | st.none(),
    max_size=st.integers(min_value=0, max_value=100) | st.none(),
    average_size=st.floats(min_value=0.0, max_value=100.0) | st.none()
)


values = st.integers() | st.text(average_size=2.0)


Strategies = st.recursive(
    st.one_of(
        st.sampled_from([
            st.none(), st.booleans(), st.randoms(), st.complex_numbers(),
            st.randoms(), st.fractions(), st.decimals(),
        ]),
        st.builds(st.just, values),
        st.builds(st.sampled_from, st.lists(values, min_size=1)),
        builds_ignoring_invalid(st.floats, st.floats(), st.floats()),
    ),
    lambda x: st.one_of(
        builds_ignoring_invalid(st.lists, x, **size_strategies),
        builds_ignoring_invalid(st.sets, x, **size_strategies),
        builds_ignoring_invalid(
            lambda v: st.tuples(*v), st.lists(x, average_size=2.0)),
        builds_ignoring_invalid(
            lambda v: st.one_of(*v),
            st.lists(x, average_size=2.0, min_size=1)),
        builds_ignoring_invalid(
            st.dictionaries, x, x,
            dict_class=st.sampled_from([dict, OrderedDict]),
            min_size=st.integers(min_value=0, max_value=100) | st.none(),
            max_size=st.integers(min_value=0, max_value=100) | st.none(),
            average_size=st.floats(min_value=0.0, max_value=100.0) | st.none()
        ),
        st.builds(lambda s, f: s.map(f), x, st.sampled_from(fns)),
    )
)


strategy_globals = dict(
    (k, getattr(st, k))
    for k in dir(st)
)

strategy_globals['OrderedDict'] = OrderedDict
strategy_globals['inf'] = float('inf')
strategy_globals['nan'] = float('nan')
strategy_globals['foo'] = foo
strategy_globals['bar'] = bar
strategy_globals['baz'] = baz


@given(Strategies)
@settings(max_examples=2000)
def test_repr_evals_to_thing_with_same_repr(strategy):
    r = repr(strategy)
    via_eval = eval(r, strategy_globals)
    r2 = repr(via_eval)
    assert r == r2
