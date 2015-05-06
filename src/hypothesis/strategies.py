# coding=utf-8

# Copyright (C) 2013-2015 David R. MacIver (david@drmaciver.com)

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

from __future__ import division, print_function, absolute_import, \
    unicode_literals

import math

from hypothesis.errors import InvalidArgument
from hypothesis.settings import Settings
from hypothesis.searchstrategy import SearchStrategy
from hypothesis.internal.compat import text_type, integer_types


def just(value):
    from hypothesis.searchstrategy.misc import JustStrategy
    return JustStrategy(value)


def none():
    return just(None)


def one_of(arg, *args):
    if not args:
        check_strategy(arg)
        return arg
    from hypothesis.searchstrategy.strategies import OneOfStrategy
    args = (arg,) + args
    for arg in args:
        check_strategy(arg)
    return OneOfStrategy(args)


def tuples(*args, **kwargs):
    tuple_class = kwargs.pop('tuple_class', None) or tuple
    for k in kwargs:
        raise TypeError('tuples() got an unexpected keyword argument %r' % (
            k,
        ))
    for arg in args:
        check_strategy(arg)
    from hypothesis.searchstrategy.collections import TupleStrategy
    return TupleStrategy(args, tuple_class)


def integers(min_value=None, max_value=None):
    from hypothesis.searchstrategy.numbers import IntegersFromStrategy, \
        BoundedIntStrategy, RandomGeometricIntStrategy, WideRangeIntStrategy

    if min_value is None:
        if max_value is None:
            return (
                RandomGeometricIntStrategy() |
                WideRangeIntStrategy()
            )
        else:
            check_type(integer_types, max_value)
            return IntegersFromStrategy(0).map(lambda x: max_value - x)
    else:
        check_type(integer_types, min_value)
        if max_value is None:
            return IntegersFromStrategy(min_value)
        else:
            if min_value == max_value:
                return just(min_value)
            elif min_value > max_value:
                raise InvalidArgument(
                    'Cannot have max_value=%r < min_value=%r' % (
                        max_value, min_value
                    ))
            return BoundedIntStrategy(min_value, max_value)


def booleans():
    from hypothesis.searchstrategy.misc import BoolStrategy
    return BoolStrategy()


def floats(min_value=None, max_value=None):
    for e in (min_value, max_value):
        if e is not None and math.isnan(e):
            raise InvalidArgument('nan is not a valid end point')

    if min_value == float('-inf'):
        min_value = None
    if max_value == float('inf'):
        max_value = None

    from hypothesis.searchstrategy.numbers import WrapperFloatStrategy, \
        GaussianFloatStrategy, BoundedFloatStrategy, ExponentialFloatStrategy,\
        JustIntFloats, NastyFloats, FullRangeFloats, \
        FixedBoundedFloatStrategy, FloatsFromBase
    if min_value is None and max_value is None:
        return WrapperFloatStrategy(
            GaussianFloatStrategy() |
            BoundedFloatStrategy() |
            ExponentialFloatStrategy() |
            JustIntFloats() |
            NastyFloats() |
            FullRangeFloats()
        )
    elif min_value is not None and max_value is not None:
        if max_value < min_value:
            raise InvalidArgument(
                'Cannot have max_value=%r < min_value=%r' % (
                    max_value, min_value
                ))
        elif min_value == max_value:
            return just(min_value)
        elif math.isinf(max_value - min_value):
            assert min_value < 0 and max_value > 0
            return floats(min_value=0, max_value=max_value) | floats(
                min_value=min_value, max_value=0
            )
        return FixedBoundedFloatStrategy(min_value, max_value)
    elif min_value is not None:
        return FloatsFromBase(
            base=min_value, sign=1,
        ) | just(float('inf'))
    else:
        assert max_value is not None
        return FloatsFromBase(
            base=max_value, sign=-1
        ) | just(float('-inf'))


def complexes():
    from hypothesis.searchstrategy.numbers import ComplexStrategy
    return ComplexStrategy(
        tuples(floats(), floats())
    )


def sampled_from(elements):
    from hypothesis.searchstrategy.misc import SampledFromStrategy
    elements = tuple(iter(elements))
    if not elements:
        raise InvalidArgument(
            'sampled_from requires at least one value'
        )
    if len(elements) == 1:
        return just(elements[0])
    return SampledFromStrategy(elements)


def check_valid_size(value):
    if value is None:
        return
    check_type(integer_types + (float,), value)
    if value < 0:
        raise InvalidArgument('Invalid size %r < 0' % (value,))
    if isinstance(value, float) and math.isnan(value):
        raise InvalidArgument('Invalid size %r' % (value,))


def lists(elements=None, max_size=None, min_size=None, average_size=None):
    check_valid_size(min_size)
    check_valid_size(max_size)
    check_valid_size(average_size)
    from hypothesis.searchstrategy.collections import ListStrategy
    if min_size is None:
        min_size = 0
    if average_size is None:
        if max_size is None:
            average_size = Settings.default.average_list_length
        else:
            average_size = (min_size + max_size) * 0.5

    if max_size is not None:
        if max_size < min_size:
            raise InvalidArgument(
                'Cannot have max_size=%r < min_size=%r' % (
                    max_size, min_size
                ))

        if max_size < average_size:
            raise InvalidArgument(
                'Cannot have max_size=%r < average_size=%r' % (
                    max_size, average_size
                ))

    if average_size < min_size:
        raise InvalidArgument(
            'Cannot have average_size=%r < min_size=%r' % (
                average_size, min_size
            ))

    if elements is None:
        if max_size is None or max_size > 0:
            raise InvalidArgument(
                'Cannot create non-empty lists without an element type'
            )
        else:
            return ListStrategy(())
    else:
        check_strategy(elements)
        base = ListStrategy((elements,), average_length=average_size)
        if min_size > 0:
            base = base.filter(lambda x: len(x) >= min_size)
        if max_size is not None:
            base = base.map(lambda x: x[:max_size])
        return base


def sets(elements=None, max_size=None):
    from hypothesis.searchstrategy.collections import SetStrategy
    if max_size == 0:
        return SetStrategy(())
    check_strategy(elements)
    return SetStrategy(
        (elements,),
        average_length=Settings.default.average_list_length
    )


def frozensets(elements=None, max_size=None):
    from hypothesis.searchstrategy.collections import FrozenSetStrategy
    return FrozenSetStrategy(sets(elements, max_size=max_size))


def dictionaries(fixed={}, variable=None, dict_class=dict):
    from hypothesis.searchstrategy.collections import FixedKeysDictStrategy

    if fixed:
        check_type((SearchStrategy, dict), fixed)
    if isinstance(fixed, SearchStrategy):
        base = fixed
    else:
        fixed = dict_class(fixed)
        for v in fixed.values():
            check_type(SearchStrategy, v)
        base = FixedKeysDictStrategy(fixed).map(dict_class)

    if variable is not None:
        if not isinstance(variable, SearchStrategy):
            from collections import Iterable
            if not isinstance(variable, Iterable):
                raise InvalidArgument(
                    'Expected variable to be iterable but got %r' % (
                        variable,))
            variable = tuple(variable)
            if len(variable) != 2:
                raise InvalidArgument(
                    'Expected two values in variable but got %r' % (
                        variable,))
            for m in variable:
                check_strategy(m)
            variable = lists(tuples(*variable)).map(dict_class)
        if not fixed:
            base = variable
        else:
            base = tuples(
                base, variable
            ).map(lambda x: dict.update(*x) or x[0])
    return base


def streaming(elements):
    check_strategy(elements)
    from hypothesis.searchstrategy.streams import StreamStrategy
    return StreamStrategy(elements)


def text(alphabet=None, average_size=None, min_size=None, max_size=None):
    from hypothesis.searchstrategy.strings import OneCharStringStrategy, \
        StringStrategy
    if alphabet is None:
        char_strategy = OneCharStringStrategy()
    elif not alphabet:
        return just('')
    elif isinstance(alphabet, SearchStrategy):
        char_strategy = alphabet
    else:
        char_strategy = sampled_from(text_type(alphabet))
    return StringStrategy(lists(
        char_strategy, average_size=average_size, min_size=min_size,
        max_size=max_size
    ))


def binary(average_size=None, min_size=None, max_size=None):
    from hypothesis.searchstrategy.strings import BinaryStringStrategy
    return BinaryStringStrategy(
        lists(
            integers(min_value=0, max_value=255),
            average_size=average_size, min_size=min_size, max_size=max_size
        )
    )


def basic(
    basic=None,
    generate_parameter=None, generate=None, simplify=None, copy=None
):
    from hypothesis.searchstrategy.basic import basic_strategy, BasicStrategy
    if basic is not None:
        if isinstance(basic, type):
            basic = basic()
        check_type(BasicStrategy, basic)
        generate_parameter = generate_parameter or basic.generate_parameter
        generate = generate or basic.generate
        simplify = simplify or basic.simplify
        copy = copy or basic.copy
    return basic_strategy(
        parameter=generate_parameter,
        generate=generate, simplify=simplify, copy=copy
    )


def randoms():
    from hypothesis.searchstrategy.misc import RandomStrategy
    return RandomStrategy(integers())


def fractions():
    from fractions import Fraction
    return tuples(integers(), integers(min_value=1)).map(
        lambda t: Fraction(*t)
    )


def decimals():
    from decimals import Decimal
    return (
        floats().map(Decimal) |
        fractions().map(
            lambda f: Decimal(f.numerator) / f.denominator
        )
    )


def check_type(typ, arg):
    if not isinstance(arg, typ):
        if isinstance(typ, type):
            typ_string = typ.__name__
        else:
            typ_string = 'one of %s' % (
                ', '.join(t.__name__ for t in typ))
        raise InvalidArgument(
            'Expected %s but got %r' % (typ_string, arg,))


def check_strategy(arg):
    check_type(SearchStrategy, arg)
