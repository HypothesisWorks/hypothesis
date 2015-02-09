# coding=utf-8

# Copyright (C) 2013-2015 David R. MacIver (david@drmaciver.com)

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

from __future__ import division, print_function, unicode_literals

from functools import wraps

from hypothesis.internal.classmap import ClassMap
from hypothesis.internal.utils.hashitanyway import HashItAnyway


class SpecificationMapper(object):

    """Maps descriptions of some type to a type. Has configurable handlers for
    what a description may look like. Handlers for descriptions may take either
    a specific value or all instances of a type and have access to the mapper
    to look up types.

    Also supports prototype based inheritance, with children being able to
    override specific handlers

    There is a single default() object per subclass of SpecificationMapper
    which everything has as a prototype if it's not assigned any other
    prototype. This allows you to define the mappers on the default object
    and have them inherited by any custom mappers you want.

    """

    @classmethod
    def default(cls):
        key = '_%s_default_mapper' % (cls.__name__,)
        try:
            return getattr(cls, key)
        except AttributeError:
            pass
        result = cls()
        setattr(cls, key, result)
        return result

    @classmethod
    def clear_default(cls):
        try:
            delattr(cls, '_%s_default_mapper' % (cls.__name__,))
        except AttributeError:
            pass

    def __init__(self, prototype=None):
        self.value_mappers = {}
        self.instance_mappers = ClassMap()
        self.__prototype = prototype
        self.__descriptor_cache = {}

    def prototype(self):
        if self.__prototype:
            return self.__prototype
        if self is self.default():
            return None
        return self.default()

    def define_specification_for(self, value, specification):
        self.value_mappers.setdefault(value, []).append(specification)
        self.clear_cache()

    def clear_cache(self):
        self.__descriptor_cache = {}

    def define_specification_for_instances(self, cls, specification):
        self.instance_mappers.setdefault(cls, []).append(specification)
        self.clear_cache()

    def define_specification_for_classes(
            self, specification, subclasses_of=None):
        if subclasses_of:
            original_specification = specification

            @wraps(specification)
            def restricted(sms, descriptor):
                if issubclass(descriptor, subclasses_of):
                    return original_specification(sms, descriptor)
                else:
                    return next_in_chain()
            specification = restricted

        self.define_specification_for_instances(
            typekey(SpecificationMapper),
            specification)
        self.clear_cache()

    def new_child_mapper(self):
        return self.__class__(prototype=self)

    def specification_for(self, descriptor):
        k = HashItAnyway(descriptor)
        try:
            return self.__descriptor_cache[k]
        except KeyError:
            pass
        r = self._calculate_specification_for(descriptor)
        self.__descriptor_cache[k] = r
        return r

    def _calculate_specification_for(self, descriptor):
        for h in self.find_specification_handlers_for(descriptor):
            try:
                r = h(self, descriptor)
                break
            except NextInChain:
                pass
        else:
            r = self.missing_specification(descriptor)

        return r

    def has_specification_for(self, descriptor):
        try:
            self.specification_for(descriptor)
            return True
        except MissingSpecification:
            return False

    def find_specification_handlers_for(self, descriptor):
        if safe_in(descriptor, self.value_mappers):
            for h in reversed(self.value_mappers[descriptor]):
                yield h
        tk = typekey(descriptor)
        for h in self.__instance_handlers(tk):
            yield h
        if self.prototype():
            for h in self.prototype().find_specification_handlers_for(
                    descriptor):
                yield h

    def __instance_handlers(self, tk):
        for hs in self.instance_mappers.all_mappings(tk):
            for h in reversed(hs):
                yield h

    def missing_specification(self, descriptor):
        raise MissingSpecification(descriptor)


def typekey(x):
    return x.__class__


def safe_in(x, ys):
    """Test if x is present in ys even if x is unhashable."""
    try:
        return x in ys
    except TypeError:
        return False


def next_in_chain():
    raise NextInChain()


class NextInChain(Exception):

    def __init__(self):
        Exception.__init__(
            self,
            "Not handled. Call next in chain. You shouldn't have seen this"
            'exception.')


class MissingSpecification(Exception):

    def __init__(self, descriptor):
        Exception.__init__(
            self,
            'Unable to produce specification for descriptor %s' %
            str(descriptor))
