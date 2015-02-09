# coding=utf-8

# Copyright (C) 2013-2015 David R. MacIver (david@drmaciver.com)

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

"""
This module introduces the concept of *basic data*.

Basic data is:

    * Any unicode string (str in python 3, unicode in python 2)
    * Any data of type: bool, int, (also long in python 2)
    * None
    * Any heterogenous list of basic data (including lists of lists, etc)

The goal of basic data is to provide a small set of primitives that a format
is responsible for marshalling and define formats for all other data in terms
of conversion to and from basic data.

A Converter is then responsible for converting data matching a particular
description to and from basic data. It essentially designs a schema for
representing values in a simpler form.

This uses a mechanism essentially identical to that of SearchStrategy for
mapping descriptors to converters.
"""


from __future__ import division, print_function, unicode_literals

import base64
import struct
from abc import abstractmethod
from random import Random

from hypothesis.descriptors import Just, OneOf, FloatRange, SampledFrom, \
    IntegerRange, one_of
from hypothesis.strategytable import StrategyTable
from hypothesis.searchstrategy import RandomWithSeed, nice_string
from hypothesis.internal.compat import hrange, text_type, binary_type, \
    integer_types
from hypothesis.internal.specmapper import SpecificationMapper
from hypothesis.internal.utils.fixers import real_index, actually_equal


class WrongFormat(ValueError):

    """An exception indicating you have attempted to serialize a value that
    does not match the type described by this format."""


class BadData(ValueError):

    """The data that we got out of the database does not seem to match the data
    we could have put into the database given this schema."""


def check_matches(strategy, value):
    if not strategy.could_have_produced(value):
        raise WrongFormat('Value %r does not match description %s' % (
            value, nice_string(strategy.descriptor)
        ))


def check_type(typ, value, e=WrongFormat):
    if not isinstance(value, typ):
        if isinstance(typ, tuple):
            name = 'any of ' + ', '.join(t.__name__ for t in typ)
        else:
            name = typ.__name__
        raise e('Value %r is not an instance of %s' % (
            value, name
        ))


def check_data_type(typ, value):
    check_type(typ, value, BadData)


def check_length(l, value):
    try:
        actual = len(value)
    except TypeError:
        raise BadData('Excepted list but got %r' % (value,))
    if actual != l:
        raise BadData('Expected %d elements but got %d from %r' % (
            l, actual, value
        ))


class NotSerializeable(Exception):

    def __init__(self, descriptor):
        super(NotSerializeable, self).__init__(
            '%s does not describe a serializeable type' % (
                nice_string(descriptor),
            )
        )


def not_serializeable(s, d):
    raise NotSerializeable(d)


class ConverterTable(SpecificationMapper):

    """Mapper defining how data is serialized from a descriptor.

    Will handle anything it doesn't understand by just throwing it
    straight to JSON.

    """

    def __init__(self, strategy_table=None):
        super(ConverterTable, self).__init__()
        self.strategy_table = strategy_table or StrategyTable.default()

    def mark_not_serializeable(self, descriptor):
        self.define_specification_for(descriptor, not_serializeable)

    def missing_specification(self, descriptor):
        return not_serializeable(self, descriptor)


for basic_type in (
    type(None), text_type, bool,
) + integer_types:
    ConverterTable.default().define_specification_for(
        basic_type,
        lambda s, d: GenericConverter(s.strategy_table.specification_for(d)))

for r in (IntegerRange, FloatRange):
    ConverterTable.default().define_specification_for_instances(
        r,
        lambda s, d: GenericConverter(s.strategy_table.specification_for(d)))


class Converter(object):

    """
    Interface for converting objects to and from an object system suitable
    for converting to the JSON-with-bigints converter that Python uses. Note:
    Does not actually serialize, only munges into a different shape.
    """

    @abstractmethod  # pragma: no cover
    def to_basic(self, value):
        """Turn this value into a JSON ready object."""

    @abstractmethod  # pragma: no cover
    def from_basic(self, value):
        """Convert this value into a JSON ready object from the original
        type."""


class GenericConverter(Converter):

    """Trivial converter that does no conversion.

    In the absence of anything more specific this will be used.

    """

    def __init__(self, strategy):
        self.strategy = strategy

    def to_basic(self, value):
        check_matches(self.strategy, value)
        return value

    def from_basic(self, value):
        if not self.strategy.could_have_produced(value):
            raise BadData('Data %r does not match description %s' % (
                value, nice_string(self.strategy.descriptor)
            ))
        return value


class FloatConverter(Converter):

    def to_basic(self, value):
        check_type(float, value)
        return struct.unpack(b'!Q', struct.pack(b'!d', value))[0]

    def from_basic(self, value):
        check_data_type(integer_types, value)
        try:
            return struct.unpack(b'!d', struct.pack(b'!Q', value))[0]
        except (struct.error, ValueError, OverflowError) as e:
            raise BadData(e.args[0])

ConverterTable.default().define_specification_for(
    float,
    lambda s, d: FloatConverter())


class ListConverter(Converter):

    """Simply maps a child strategy over its elements as lists are natively
    supported."""

    def __init__(self, child_converter):
        self.child_converter = child_converter

    def to_basic(self, value):
        check_type(list, value)
        return list(map(self.child_converter.to_basic, value))

    def from_basic(self, value):
        check_data_type(list, value)
        return list(map(self.child_converter.from_basic, value))


def define_list_converter(converters, descriptor):
    element_converter = converters.specification_for(one_of(descriptor))
    if isinstance(element_converter, GenericConverter):
        return GenericConverter(
            converters.strategy_table.specification_for(descriptor))
    else:
        return ListConverter(element_converter)

ConverterTable.default().define_specification_for_instances(
    list, define_list_converter)


class CollectionConverter(Converter):

    """
    Round-trips a collection type via a list
    """

    def __init__(self, list_converter, collection_type):
        self.list_converter = list_converter
        self.collection_type = collection_type

    def to_basic(self, value):
        check_type(self.collection_type, value)
        return self.list_converter.to_basic(list(value))

    def from_basic(self, value):
        check_data_type(list, value)
        return self.collection_type(self.list_converter.from_basic(value))


def define_collection_converter(converters, descriptor):
    return CollectionConverter(
        converters.specification_for(list(descriptor)),
        type(descriptor),
    )

ConverterTable.default().define_specification_for_instances(
    set, define_collection_converter)
ConverterTable.default().define_specification_for_instances(
    frozenset, define_collection_converter)


class ComplexConverter(Converter):

    """Encodes complex numbers as a list [real, imaginary]"""

    def __init__(self, float_converter):
        self.float_converter = float_converter

    def to_basic(self, value):
        check_type(complex, value)
        return list(
            map(self.float_converter.to_basic, [value.real, value.imag]))

    def from_basic(self, c):
        check_length(2, c)
        check_data_type(integer_types, c[0])
        check_data_type(integer_types, c[1])
        return complex(*map(self.float_converter.from_basic, c))

ConverterTable.default().define_specification_for(
    complex, lambda s, d: ComplexConverter(s.specification_for(float)))


class TextConverter(Converter):

    """Text types which are guaranteed to be unicode clean are stored as normal
    JSON strings."""

    def to_basic(self, c):
        check_type(text_type, c)
        return c

    def from_basic(self, c):
        check_data_type(text_type, c)
        return text_type(c)

ConverterTable.default().define_specification_for(
    text_type, lambda s, d: TextConverter()
)


class BinaryConverter(Converter):

    """Binary types are base 64 encoded.

    Note that this includes str in python 2.7
    because it has no associated encoding. Use unicode objects in 2.7 if you
    care about human readable database converters.

    """

    def to_basic(self, value):
        check_type(binary_type, value)
        return base64.b64encode(value).decode('utf-8')

    def from_basic(self, data):
        check_data_type(text_type, data)
        try:
            return base64.b64decode(data.encode('utf-8'))
        except Exception as e:
            raise BadData(*e.args)

ConverterTable.default().define_specification_for(
    binary_type, lambda s, d: BinaryConverter()
)


class RandomConverter(Converter):

    """Stores one of hypothesis's RandomWithSeed types just by storing it as
    its seed value."""

    def to_basic(self, value):
        check_type(RandomWithSeed, value)
        check_type(integer_types, value.seed)
        return value.seed

    def from_basic(self, c):
        check_data_type(integer_types, c)
        return RandomWithSeed(c)

ConverterTable.default().define_specification_for(
    Random, lambda s, d: RandomConverter()
)


class JustConverter(Converter):

    """Just can only have a single value!

    We just represent this as a  null object and recover it as the
    value.

    """

    def __init__(self, value):
        self.value = value

    def to_basic(self, c):
        if not actually_equal(c, self.value):
            raise WrongFormat('%r != %r' % (c, self.value))
        return None

    def from_basic(self, c):
        if c is not None:
            raise BadData('Expected None value but got %r' % (c,))
        return self.value


ConverterTable.default().define_specification_for_instances(
    Just,
    lambda s, d: JustConverter(d.value)
)


class TupleConverter(Converter):

    """Tuples are stored as lists of the correct length with each coordinate
    stored in its corresponding converters."""

    def __init__(self, tuple_converters, tuple_type):
        self.tuple_type = tuple_type
        self.tuple_converters = tuple(tuple_converters)

    def to_basic(self, value):
        check_type(self.tuple_type, value)
        if len(self.tuple_converters) != len(value):
            raise WrongFormat((
                'Value %r is of the wrong length. '
                'Expected %d elements but got %d'
            ) % (
                value, len(self.tuple_converters), len(value),
            ))
        if len(self.tuple_converters) == 1:
            return self.tuple_converters[0].to_basic(value[0])
        return [
            f.to_basic(v)
            for f, v in zip(self.tuple_converters, value)
        ]

    def from_basic(self, value):
        if len(self.tuple_converters) == 1:
            return (self.tuple_converters[0].from_basic(value),)
        check_length(len(self.tuple_converters), value)
        return self.new_tuple(
            f.from_basic(v)
            for f, v in zip(self.tuple_converters, value)
        )

    def new_tuple(self, value):
        value = tuple(value)
        if self.tuple_type == tuple:
            return value
        else:
            return self.tuple_type(*value)


ConverterTable.default().define_specification_for_instances(
    tuple,
    lambda s, d: TupleConverter(
        (s.specification_for(x) for x in d),
        type(d),
    )
)


class FixedKeyDictConverter(Converter):

    """
    Dicts are *not* stored as dicts. This is for a mix of reasons, but mostly
    that python supports a much greater range of keys than JSON does and we
    would have to find a way to encode them. Instead the keys are given an
    arbitrary but well defined order and the dict is serialized as per a tuple
    in that order.
    """

    def __init__(self, dict_strategy, dict_of_converters):
        keys = tuple(
            sorted(
                dict_of_converters.keys(),
                key=lambda t: (t.__class__.__name__, repr(t)))
        )
        self.strategy = dict_strategy
        self.converters = tuple(
            (k, dict_of_converters[k]) for k in keys
        )

    def to_basic(self, value):
        check_matches(self.strategy, value)
        return [
            f.to_basic(value[k])
            for k, f in self.converters
        ]

    def from_basic(self, value):
        check_length(len(self.converters), value)
        return {
            k: f.from_basic(v)
            for (k, f), v in zip(self.converters, value)
        }


ConverterTable.default().define_specification_for_instances(
    dict,
    lambda s, d: FixedKeyDictConverter(
        s.strategy_table.strategy(d),
        {
            k: s.specification_for(v)
            for k, v in d.items()
        })
)


class OneOfConverter(Converter):

    """OneOf stores its elements as pairs [integer tag, value] where the tag is
    the position of the first strategy in the list that could have produced it.

    There is some unavoidable ambiguity here where strategies can
    overlap but hopefully they have the property that on overlap their
    converters agree. This is the case for all the built in converters.
    You'll still get a result where it's not but it may result in some
    things being changed slightly.

    """

    def __init__(self, converters, strategies):
        assert len(converters) == len(strategies)
        self.converters = converters
        self.strategies = strategies

    def to_basic(self, value):
        for i in hrange(len(self.converters)):  # pragma: no branch
            if self.strategies[i].could_have_produced(value):
                return [i, self.converters[i].to_basic(value)]
        raise WrongFormat('Value %r does not match any of %s' % (
            value, ', '.join(
                nice_string(s.descriptor) for s in self.strategies)))

    def from_basic(self, value):
        check_length(2, value)
        check_data_type(integer_types, value[0])
        i, x = value
        if i < 0 or i >= len(self.converters):
            raise BadData('Invalid index %d into %d elements' % (
                i, len(self.converters)
            ))
        return self.converters[i].from_basic(x)


def define_one_of_converter(converter_table, descriptor):
    converters = [
        converter_table.specification_for(v) for v in descriptor.elements]
    strategies = [
        converter_table.strategy_table.specification_for(v)
        for v in descriptor.elements
    ]
    return OneOfConverter(converters, strategies)

ConverterTable.default().define_specification_for_instances(
    OneOf, define_one_of_converter
)


class SampledFromConverter(Converter):

    """A SampledFrom instance is simply stored as an integer index into the
    list of values sampled from."""

    def __init__(self, choices):
        self.choices = tuple(choices)

    def to_basic(self, value):
        try:
            return real_index(self.choices, value)
        except ValueError:
            raise WrongFormat('%r is not in %r' % (value, self.choices,))

    def from_basic(self, value):
        check_data_type(integer_types, value)
        if value < 0 or value >= len(self.choices):
            raise BadData('Invalid index %d into %d elements' % (
                value, len(self.choices)
            ))
        return self.choices[value]


ConverterTable.default().define_specification_for_instances(
    SampledFrom, lambda s, d: SampledFromConverter(d.elements)
)
