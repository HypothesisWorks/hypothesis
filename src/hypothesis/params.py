# coding=utf-8

# Copyright (C) 2013-2015 David R. MacIver (david@drmaciver.com)

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

"""This module defines a Parameter type which is used by search strategies to
control the shape of their distribution.

It also provides a variety of implementations thereof.

"""
from __future__ import division, print_function, unicode_literals

import inspect
import collections
from abc import abstractmethod

import hypothesis.internal.utils.distributions as dist


class Parameter(object):

    """Represents a distribution of values of some type.

    These values can be drawn given a random number generator.

    """

    def __init__(self):
        pass

    @abstractmethod  # pragma: no cover
    def draw(self, random):
        """Draw a value at random, using only state from the provided random
        number generator."""


class ExponentialParameter(Parameter):

    """Parameter representing an exponential distribution over floats."""

    def __init__(self, lambd):
        Parameter.__init__(self)
        if lambd <= 0:
            raise ValueError(
                'Invalid lambda %f for exponential distribution' % (lambd,))
        self.lambd = lambd

    def draw(self, random):
        return random.expovariate(self.lambd)


class BetaFloatParameter(Parameter):

    """Parameter representing a beta distribution over floats."""

    def __init__(self, alpha, beta):
        Parameter.__init__(self)
        self.alpha = alpha
        self.beta = beta

    def draw(self, random):
        return random.betavariate(alpha=self.alpha, beta=self.beta)


class UniformFloatParameter(Parameter):

    """Parameter representing a uniform distribution over floats between a
    provided lower and upper bound."""

    def __init__(self, lower_bound, upper_bound):
        Parameter.__init__(self)
        self.lower_bound = lower_bound
        self.upper_bound = upper_bound

    def draw(self, random):
        return self.lower_bound + (
            self.upper_bound - self.lower_bound
        ) * random.random()


class UniformIntParameter(Parameter):

    """Parameter representing a uniform distribution over floats between a
    provided lower and upper bound."""

    def __init__(self, lower_bound, upper_bound):
        Parameter.__init__(self)
        self.lower_bound = lower_bound
        self.upper_bound = upper_bound

    def draw(self, random):
        return random.randint(self.lower_bound, self.upper_bound)


class NormalParameter(Parameter):

    """Parameter representing a normal distribution over floats with a provided
    mean and variance."""

    def __init__(self, mean, variance):
        Parameter.__init__(self)
        self.mean = mean
        self.sd = variance ** 0.5

    def draw(self, random):
        return random.normalvariate(self.mean, self.sd)


class GammaParameter(Parameter):

    """Parameter representing a gamma distribution over floats.

    This is useful as e.g. a prior for an exponential distribution.

    """

    def __init__(self, alpha, beta):
        Parameter.__init__(self)
        self.alpha = alpha
        self.beta = beta

    def draw(self, random):
        return random.gammavariate(self.alpha, self.beta)


class NonEmptySubset(Parameter):

    """
    A parameter which draws non-empty subsets from some set. Each element of
    the set is drawn with equal probability and independently of all others.
    By default the probability is chosen to give very few elements.
    """

    def __init__(self, elements, activation_chance=None):
        Parameter.__init__(self)
        self.elements = tuple(elements)
        if not elements:
            raise ValueError('Must have at least one element')
        if activation_chance is None:
            # TODO: This should have a more principled choice. It seems to be
            # good in practice though.
            # Note: The actual expected value is slightly higher because we're
            # conditioning on the result being non-empty.
            if len(elements) == 1:
                desired_expected_value = 1.0
            elif len(elements) <= 3:
                desired_expected_value = 1.75
            else:
                desired_expected_value = 2.0
            activation_chance = desired_expected_value / len(elements)
        self.activation_chance = activation_chance

    def draw(self, random):
        if len(self.elements) == 1:
            return [self.elements[0]]
        result = []
        while not result:
            result = [
                x
                for x in self.elements
                if dist.biased_coin(random, self.activation_chance)
            ]
        return result


class BiasedCoin(Parameter):

    """A parameter which draws a boolean value which is True with some fixed
    probability."""

    def __init__(self, probability):
        Parameter.__init__(self)
        if probability <= 0 or probability >= 1:
            raise ValueError(
                'Value %f out of valid range (0, 1)' % (probability,))
        self.probability = probability

    def draw(self, random):
        return dist.biased_coin(random, self.probability)


class DictParameter(Parameter):

    """
    A parameter which returns a dict with a fixed set of keys.
    Given an __init__ argument {k: v} this will return results from
    {k: v.draw}
    """

    def __init__(self, dict_of_parameters):
        Parameter.__init__(self)
        self.dict_of_parameters = dict(dict_of_parameters)

    def draw(self, random):
        result = {}
        for key, value in self.dict_of_parameters.items():
            result[key] = value.draw(random)
        return result


class CompositeParameter(Parameter):

    """A parameter returning a record with attributes corresponding to some
    other parameters.

    The result will be either a tuple or a namedtuple specific to this
    parameter depending on whether there are any kwargs passed.

    """

    def __init__(self, *args, **kwargs):
        Parameter.__init__(self)
        if not kwargs and len(args) == 1 and inspect.isgenerator(args[0]):
            args = tuple(args[0])
        is_pure_tuple = not kwargs
        children = []
        for index, param in enumerate(args):
            name = 'arg%d' % (index,)
            if name in kwargs:
                raise ValueError('Duplicate parameter name %s' % (name,))
            kwargs[name] = param
            children.append(name)

        for key, value in sorted(kwargs.items()):
            if hasattr(self, key):
                raise ValueError('Invalid parameter name %s' % (key,))
            if key not in children:
                children.append(key)
            setattr(self, key, value)
        self.children = tuple(children)
        if is_pure_tuple:
            self.Result = tuple
        else:
            self.Result = collections.namedtuple('Result', self.children)

    def draw(self, random):
        bits = [
            getattr(self, c).draw(random) for c in self.children
        ]
        if self.Result == tuple:
            return tuple(bits)
        else:
            return self.Result(*bits)
