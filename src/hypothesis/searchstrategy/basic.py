# coding=utf-8

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# Most of this work is copyright (C) 2013-2015 David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
# https://github.com/DRMacIver/hypothesis/blob/master/CONTRIBUTING.rst for a
# full list of people who may hold copyright, and consult the git log if you
# need to determine who owns an individual contribution.

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

from __future__ import division, print_function, absolute_import

import hashlib
from copy import deepcopy
from random import Random
from weakref import WeakKeyDictionary

import hypothesis.internal.distributions as dist
from hypothesis.settings import Settings
from hypothesis.internal.compat import hrange, integer_types

from .strategies import strategy, check_length, SearchStrategy, \
    check_data_type


class BasicStrategy(object):

    """
    A class for constructing strategies which exposes a kinder, friendlier,
    interface for you to use. It gives you 80-90% of Hypothesis's strategy
    functionality but presents a stable and less outlandishly complicated
    API, closer in nature to the standard Quickcheck arbitrary + simplify
    API, but with a few variations that have proven their worth.

    Caveats for the unwary:

        * This is not actually a  SearchStrategy subclass and is not nearly
          as close to the metal as you might imagine.
        * Consider building your strategies out of existing strategies rather
          than using this if at all possible. Writing a good strategy is hard
          work and the built in types frequently have a lot of careful tuning
          to hit edge cases that your own implementations will not get to
          take advantage of.
    """

    def __init__(self, settings=None):
        self.settings = settings or Settings.default

    def generate_parameter(self, random):
        """A parameter value gets used to choose the "shape" of your
        distribution. Values drawn from this will be fed to generate, with the
        same value often being used multiple times.

        This is used to drive the adaptic exploration, so you should try to
        make sure that your parameters determine something interesting that
        is likely to affect things people care about - parameters which tend
        to produce results that fail assume will be used less often than
        parameters which tend to produce things that pass assume.

        However Hypothesis will work perfectly well if you don't want to use
        this feature and the default implementation of just returning None is
        entirely acceptable.

        """
        return None

    def generate(self, random, parameter_value):
        """Generate a value given a random number generator and a value that
        has previously been produced from generate_parameter.

        This is the only method you actually have to implement.

        """
        raise NotImplementedError(u'BasicStrategy.generate')

    def simplify(self, random, value):
        """Given a random number generator and a value, return a collection of
        "simpler" versions of the value.

        There should be no cycles in the graph produced by this. i.e. there
        should not be any sequence of values x1, ..., xn such that x{i+1} is
        in simplify(xi) and x1 is in simplify xn. Hypothesis has built in
        limits which will stop it getting stuck in an infinite loop if you do
        this, but it will tend to get fixated on any values it finds in a loop,
        and will take longer to give you a good answer.

        In general simplify should make a good effort to shrink a value a lot.
        "By about half" is usually a good choice for the initial values of the
        generator, with values closer to the original value appearing towards
        the end.

        It's fine to not implement this but your examples will be
        correspondingly more complex if you do.

        """
        return ()

    def copy(self, value):
        """Copy a value so that the result is safe to be passed to a function
        that might mutate it. Any mutations to the result should not affect the
        original.

        The default implementation of this uses deepcopy and should
        generally be entirely safe to use. Only override this if your
        value doesn't and can't be made to support deepcopying.

        """
        return deepcopy(value)


class BasicTemplate(object):

    def __init__(self, tracking_id):
        self.tracking_id = tracking_id

    def __trackas__(self):
        return (type(self).__name__, self.tracking_id)

    def __eq__(self, other):
        return (
            type(self) == type(other) and
            self.tracking_id == other.tracking_id
        )

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(self.tracking_id)


def add_int_to_hasher(hasher, i):
    hasher.update(str(i).encode(u'utf-8'))


class Generated(BasicTemplate):

    def __init__(self, template_seed, parameter_seed):
        hasher = hashlib.sha1()
        add_int_to_hasher(hasher, template_seed)
        add_int_to_hasher(hasher, parameter_seed)
        super(Generated, self).__init__(hasher.digest())
        self.template_seed = template_seed
        self.parameter_seed = parameter_seed
        self.depth = 0


class Simplified(BasicTemplate):

    def __init__(self, seed, iteration, source):
        hasher = hashlib.sha1()
        hasher.update(source.tracking_id)
        add_int_to_hasher(hasher, seed)
        add_int_to_hasher(hasher, iteration)
        super(Simplified, self).__init__(hasher.digest())
        self.seed = seed
        self.iteration = iteration
        self.source = source
        self.depth = source.depth + 1


class BasicSearchStrategy(SearchStrategy):

    # We don't have good duplicate detection for this so we cut off
    # simplification at an arbitrary level so as to not get caught in an
    # infinite loop.
    MAX_DEPTH = 1000

    def __init__(
        self,
        user_generate, user_parameter=None, user_simplify=None,
        copy_value=deepcopy,
    ):
        self.user_generate = user_generate
        self.user_parameter = user_parameter
        self.user_simplify = user_simplify or (lambda r, x: ())
        self.reify_cache = WeakKeyDictionary()
        self.copy_value = copy_value

    def __repr__(self):
        def name_if(x):
            return x.__name__ if x else repr(x)

        return (
            u'BasicSearchStrategy(generate=%s, '
            u'parameter=%s, simplify=%s)'
        ) % (
            name_if(self.user_generate),
            name_if(self.user_parameter),
            name_if(self.user_simplify),
        )

    def draw_parameter(self, random):
        if self.user_parameter is not None:
            up = random.getrandbits(64)
        else:
            up = 0
        n_distinct_templates = dist.geometric(random, random.random())
        template_choices = tuple(
            random.getrandbits(64)
            for _ in hrange(n_distinct_templates)
        )
        return (up, template_choices)

    def draw_template(self, random, parameter):
        up, template_choices = parameter
        if template_choices:
            return Generated(
                random.choice(template_choices), up
            )
        else:
            return Generated(
                random.getrandbits(64), up
            )

    def strictly_simpler(self, x, y):
        return x.depth > y.depth

    def basic_simplify(self, random, template):
        if template.depth >= self.MAX_DEPTH:
            return
        random_seed = random.getrandbits(64)
        reified = self.reify(template)
        for i, simpler in enumerate(
            self.user_simplify(Random(random_seed), reified)
        ):
            new_template = Simplified(
                source=template, seed=random_seed, iteration=i
            )
            self.reify_cache[new_template] = simpler
            yield new_template

    def reify(self, template):
        try:
            return self.reify_cache[template]
        except KeyError:
            pass

        if isinstance(template, Generated):
            if self.user_parameter is None:
                parameter = None
            else:
                parameter = self.user_parameter(
                    Random(template.parameter_seed))
            result = self.user_generate(
                Random(template.template_seed), parameter)
        else:
            assert isinstance(template, Simplified)
            children = []
            current = template
            while True:
                if current in self.reify_cache:
                    break
                if isinstance(current, Generated):
                    break
                current = current.source
                children.append(current)
            while children:
                c = children.pop()
                self.reify(c)
                assert c in self.reify_cache
            result = self.reify(template.source)
            for i, value in enumerate(  # pragma: no branch
                self.user_simplify(Random(template.seed), result)
            ):
                if i == template.iteration:
                    result = value
                    break
        self.reify_cache[template] = result
        return self.copy_value(result)

    def to_basic(self, template):
        simplifications = []
        while isinstance(template, Simplified):
            simplifications.append([template.seed, template.iteration])
            template = template.source
        assert isinstance(template, Generated)
        return [
            template.template_seed, template.parameter_seed, simplifications]

    def from_basic(self, data):
        check_data_type(list, data)
        check_length(3, data)
        check_data_type(integer_types, data[0])
        check_data_type(integer_types, data[1])
        template = Generated(data[0], data[1])
        simplifications = data[2]
        check_data_type(list, simplifications)
        while simplifications:
            step = simplifications.pop()
            check_data_type(list, step)
            check_length(2, step)
            seed, iteration = step
            template = Simplified(
                seed=seed, iteration=iteration, source=template)
        return template


def basic_strategy(
    generate,
    parameter=None, simplify=None, copy=deepcopy,
):
    return BasicSearchStrategy(
        user_generate=generate, user_parameter=parameter,
        user_simplify=simplify, copy_value=copy,
    )


@strategy.extend(BasicStrategy)
def basic_to_strategy(basic, settings):
    return basic_strategy(
        generate=basic.generate,
        parameter=basic.generate_parameter,
        simplify=basic.simplify, copy=basic.copy
    )


@strategy.extend_static(BasicStrategy)
def basic_class_to_strategy(cls, settings):
    return strategy(cls(settings))
