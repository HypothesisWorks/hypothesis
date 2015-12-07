# coding=utf-8
#
# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)
#
# Most of this work is copyright (C) 2013-2015 David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
# https://github.com/DRMacIver/hypothesis/blob/master/CONTRIBUTING.rst for a
# full list of people who may hold copyright, and consult the git log if you
# need to determine who owns an individual contribution.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.
#
# END HEADER

from __future__ import division, print_function, absolute_import

from hypothesis.settings import Settings, note_deprecation
from hypothesis.internal.compat import quiet_raise
from hypothesis.utils.extmethod import ExtMethod


class StrategyExtMethod(ExtMethod):

    def __init__(self, *args, **kwargs):
        super(StrategyExtMethod, self).__init__(*args, **kwargs)
        self.loaded_deprecated_api = False

    def load_deprecated_api(self):
        if self.loaded_deprecated_api:
            return
        self.loaded_deprecated_api = True

        import hypothesis.strategies as st
        import hypothesis.specifiers as spec
        from hypothesis.searchstrategy.basic import BasicStrategy, \
            basic_strategy
        from hypothesis.searchstrategy.narytree import NAryTree, \
            NAryTreeStrategy
        from random import Random
        from decimal import Decimal
        from fractions import Fraction
        from hypothesis.internal.compat import text_type, binary_type

        @self.extend(tuple)
        def define_tuple_strategy(specifier, settings):
            from hypothesis.searchstrategy.collections import TupleStrategy
            return TupleStrategy(
                tuple(strategy(d, settings) for d in specifier),
                tuple_type=type(specifier)
            )

        @self.extend(dict)
        def define_dict_strategy(specifier, settings):
            strategy_dict = {}
            for k, v in specifier.items():
                strategy_dict[k] = self(v, settings)
            return st.fixed_dictionaries(strategy_dict)

        @self.extend(spec.Dictionary)
        def define_dictionary_strategy(specifier, settings):
            return strategy(
                [(specifier.keys, specifier.values)], settings
            ).map(specifier.dict_class)

        @self.extend(spec.IntegerRange)
        def define_strategy_for_integer_Range(specifier, settings):
            return st.integers(
                min_value=specifier.start, max_value=specifier.end)

        @self.extend(spec.FloatRange)
        def define_strategy_for_float_Range(specifier, settings):
            return st.floats(specifier.start, specifier.end)

        @self.extend_static(int)
        def int_strategy(specifier, settings):
            return st.integers()

        @self.extend(spec.IntegersFrom)
        def integers_from_strategy(specifier, settings):
            return st.integers(min_value=specifier.lower_bound)

        @self.extend_static(float)
        def define_float_strategy(specifier, settings):
            return st.floats()

        @self.extend_static(complex)
        def define_complex_strategy(specifier, settings):
            return st.complex_numbers()

        @self.extend_static(Decimal)
        def define_decimal_strategy(specifier, settings):
            return st.decimals()

        @self.extend_static(Fraction)
        def define_fraction_strategy(specifier, settings):
            return st.fractions()

        @self.extend(set)
        def define_set_strategy(specifier, settings):
            if not specifier:
                return st.sets(max_size=0)
            else:
                with settings:
                    return st.sets(st.one_of(
                        *[self(s, settings) for s in specifier]))

        @self.extend(frozenset)
        def define_frozen_set_strategy(specifier, settings):
            if not specifier:
                return st.frozensets(max_size=0)
            else:
                with settings:
                    return st.frozensets(
                        st.one_of(*[self(s, settings) for s in specifier]))

        @self.extend(list)
        def define_list_strategy(specifier, settings):
            if not specifier:
                return st.lists(max_size=0)
            else:
                with settings:
                    return st.lists(
                        st.one_of(*[self(s, settings) for s in specifier]))

        @self.extend_static(bool)
        def bool_strategy(cls, settings):
            return st.booleans()

        @self.extend(spec.Just)
        def define_just_strategy(specifier, settings):
            return st.just(specifier.value)

        @self.extend_static(Random)
        def define_random_strategy(specifier, settings):
            return st.randoms()

        @self.extend(spec.SampledFrom)
        def define_sampled_strategy(specifier, settings):
            return st.sampled_from(specifier.elements)

        @self.extend(type(None))
        @self.extend_static(type(None))
        def define_none_strategy(specifier, settings):
            return st.none()

        @self.extend(spec.OneOf)
        def strategy_for_one_of(oneof, settings):
            return st.one_of(*[self(d, settings) for d in oneof.elements])

        @self.extend(spec.Strings)
        def define_text_type_from_alphabet(specifier, settings):
            return st.text(alphabet=specifier.alphabet)

        @self.extend_static(text_type)
        def define_text_type_strategy(specifier, settings):
            return st.text()

        @self.extend_static(binary_type)
        def define_binary_strategy(specifier, settings):
            return st.binary()

        @self.extend(spec.Streaming)
        def stream_strategy(stream, settings):
            return st.streaming(strategy(stream.data, settings))

        @self.extend(BasicStrategy)
        def basic_to_strategy(basic, settings):
            return basic_strategy(
                generate=basic.generate,
                parameter=basic.generate_parameter,
                simplify=basic.simplify, copy=basic.copy
            )

        @self.extend_static(BasicStrategy)
        def basic_class_to_strategy(cls, settings):
            return strategy(cls(settings))

        @self.extend(NAryTree)
        def nary_tree_strategy(specifier, settings):
            return NAryTreeStrategy(specifier, settings)

    def __call__(self, specifier, settings=None):
        from hypothesis.searchstrategy.strategies import SearchStrategy

        if isinstance(specifier, SearchStrategy):
            return specifier

        self.load_deprecated_api()

        if settings is None:
            settings = Settings()

        try:
            result = super(StrategyExtMethod, self).__call__(
                specifier, settings)
        except NotImplementedError:
            quiet_raise(NotImplementedError((
                'Expected a SearchStrategy but got %r of type %s. '
                'Note: This is a NotImplementedError for legacy reasons and '
                'will become an InvalidArgumentError in Hypothesis 2.0.'
            ) % (specifier, type(specifier).__name__)))
        note_deprecation((
            'Conversion of %r to strategy is deprecated '
            'and will be removed in Hypothesis 2.0. Use %r instead.') % (
                specifier, result
        ), settings)

        assert isinstance(result, SearchStrategy)
        return result


strategy = StrategyExtMethod()
