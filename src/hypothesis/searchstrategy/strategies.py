# coding=utf-8

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# Most of this work is copyright (C) 2013-2015 David R. MacIver
# (david@drmaciver.com), but it contains contributions by other. See
# https://github.com/DRMacIver/hypothesis/blob/master/CONTRIBUTING.rst for a
# full list of people who may hold copyright, and consult the git log if you
# need to determine who owns an individual contribution.

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

from __future__ import division, print_function, absolute_import, \
    unicode_literals

from random import Random
from collections import namedtuple

from hypothesis.errors import BadData, NoExamples, WrongFormat, \
    UnsatisfiedAssumption
from hypothesis.control import assume
from hypothesis.settings import Settings
from hypothesis.deprecation import note_deprecation
from hypothesis.internal.compat import hrange, integer_types
from hypothesis.utils.extmethod import ExtMethod
from hypothesis.internal.chooser import chooser
from hypothesis.utils.conventions import not_set


class StrategyExtMethod(ExtMethod):

    def __call__(self, specifier, settings=None):
        if isinstance(specifier, SearchStrategy):
            return specifier

        if settings is None:
            settings = Settings()

        note_deprecation((
            'Calling strategy with non-strategy object %s is deprecated '
            'and will be removed in Hypothesis 2.0. Use the functions in '
            'hypothesis.strategies instead.') % (
                repr(specifier),
        ), settings)

        result = super(StrategyExtMethod, self).__call__(specifier, settings)
        assert isinstance(result, SearchStrategy)
        return result


strategy = StrategyExtMethod()


Infinity = float('inf')
EFFECTIVELY_INFINITE = 2 ** 32


def infinitish(x):
    assert x >= 0
    if x >= EFFECTIVELY_INFINITE:
        return Infinity
    else:
        return int(x)


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


def check_length(l, value, e=BadData):
    try:
        actual = len(value)
    except TypeError:
        raise e('Expected type with length but got %r' % (value,))
    if actual != l:
        raise e('Expected %d elements but got %d from %r' % (
            l, actual, value
        ))


def one_of_strategies(xs):
    """Helper function for unioning multiple strategies."""
    xs = tuple(xs)
    if not xs:
        raise ValueError('Cannot join an empty list of strategies')
    if len(xs) == 1:
        return xs[0]
    return OneOfStrategy(xs)


class SearchStrategy(object):

    """A SearchStrategy is an object that knows how to explore data of a given
    type.

    Except where noted otherwise, methods on this class are not part of the
    public API and their behaviour may change significantly between minor
    version releases. They will generally be stable between patch releases.

    With that in mind, here is how SearchStrategy works.

    A search strategy is responsible for generating, simplifying and
    serializing examples for saving.

    In order to do this a strategy has three types (where type here is more
    precise than just the class of the value. For example a tuple of ints
    should be considered different from a tuple of strings):

    1. The strategy parameter type
    2. The strategy template type
    3. The generated type

    Of these, the first two should be considered to be private implementation
    details of a strategy and the only valid thing to do them is to pass them
    back to the search strategy. Additionally, templates may be compared for
    equality and hashed.

    Templates must be of quite a restricted type. A template may be any of the
    following:

    1. Any instance of the types bool, float, int, str (unicode on 2.7)
    2. None
    3. Any tuple or namedtuple of valid template types
    4. Any frozenset of valid template types

    This may be relaxed a bit in future, but the requirement that templates are
    hashable probably won't be.

    This may all seem overly complicated but it's for a fairly good reason.
    For more discussion of the motivation see
    http://hypothesis.readthedocs.org/en/master/internals.html

    Given these, data generation happens in three phases:

    1. Draw a parameter value from a random number (defined by
       draw_parameter)
    2. Given a parameter value and a Random, draw a random template
    3. Reify a template value, deterministically turning it into a value of
       the desired type.

    Data simplification proceeds on template values, taking a template and
    providing a generator over some examples of similar but simpler templates.

    """

    def example(self):
        """Provide an example of the sort of value that this strategy
        generates. This is biased to be slightly simpler than is typical for
        values from this strategy, for clarity purposes.

        This method shouldn't be taken too seriously. It's here for interactive
        exploration of the API, not for any sort of real testing.

        This method is part of the public API.

        """
        random = Random()

        parts = []

        for _ in hrange(20):
            if len(parts) >= 3:
                break
            try:
                template = self.draw_and_produce(random)
                reified = self.reify(template)
                parts.append((template, reified))
            except UnsatisfiedAssumption:
                pass
        if not parts:
            raise NoExamples(
                'Could not find any valid examples in 20 tries'
            )

        return min(parts, key=lambda tr: self.__template_size(tr[0]))[1]

    def map(self, pack):
        """Returns a new strategy that generates values by generating a value
        from this strategy and then calling pack() on the result, giving that.

        This method is part of the public API.

        """
        return MappedSearchStrategy(
            pack=pack, strategy=self
        )

    def flatmap(self, expand):
        """Returns a new strategy that generates values by generating a value
        from this strategy, say x, then generating a value from
        strategy(expand(x))

        This method is part of the public API.

        """
        return FlatMapStrategy(
            expand=expand, strategy=self
        )

    def filter(self, condition):
        """Returns a new strategy that generates values from this strategy
        which satisfy the provided condition. Note that if the condition is too
        hard to satisfy this might result in your tests failing with
        Unsatisfiable.

        This method is part of the public API.

        """
        return FilteredStrategy(
            condition=condition,
            strategy=self,
        )

    def __or__(self, other):
        """Return a strategy which produces values by randomly drawing from one
        of this strategy or the other strategy.

        This method is part of the public API.

        """
        if not isinstance(other, SearchStrategy):
            raise ValueError('Cannot | a SearchStrategy with %r' % (other,))
        return one_of_strategies((self, other))

    # HERE BE DRAGONS. All below is non-public API of varying degrees of
    # stability.

    # Methods to be overridden by subclasses

    def draw_parameter(self, random):
        """Produce a random valid parameter for this strategy, using only data
        from the provided random number generator."""
        raise NotImplementedError(  # pragma: no cover
            '%s.draw_parameter()' % (self.__class__.__name__))

    def draw_template(self, random, parameter_value):
        """Given this Random and this parameter value, produce a random valid
        template for this strategy."""
        raise NotImplementedError(  # pragma: no cover
            '%s.draw_template()' % (self.__class__.__name__))

    def reify(self, template):
        """Given a template value, deterministically convert it into a value of
        the desired final type."""
        raise NotImplementedError(  # pragma: no cover
            '%s.reify()' % (self.__class__.__name__))

    def to_basic(self, template):
        """Convert a template value for this strategy into basic data.

        Basic data is any of:

            1. A bool, None, an int that fits into 64 bits, or a unicode string
            2. A list of basic data

        """
        raise NotImplementedError(  # pragma: no cover
            '%s.to_basic()' % (self.__class__.__name__))

    def from_basic(self, value):
        """Convert basic data back to a template, raising BadData if the
        provided data cannot be converted into a valid template for this
        strategy.

        It is not required that from_basic(to_basic(template)) == template. It
        is however required that to_basic(from_basic(data)) == data (if this
        does not raise an exception).

        """
        raise NotImplementedError(  # pragma: no cover
            '%s.from_basic()' % (self.__class__.__name__))

    # Gory implementation details

    #: Provide an upper bound on the number of available templates.
    #: The intended interpretation is that template_upper_bound means "if
    #: you've only found this many templates don't worry about it". It is also
    #: used internally in a few places for certain optimisations.
    #: Generally speaking once this reaches numbers >= 2 ** 32 or so you might
    #: as well just return float('inf').
    #: Note that there may be more distinct templates than there are
    #: representable values, because some templates may not reify and some may
    #: lead to the same value.
    template_upper_bound = Infinity

    def __init__(self):
        pass

    def draw_and_produce(self, random):
        return self.draw_template(random, self.draw_parameter(random))

    def __template_size(self, template):
        """Gives an approximate estimate of how "large" this template value is.

        This doesn't really matter for anything, it's just a convenience
        used to implement example().

        """
        def basic_size(x):
            try:
                if len(x) == 1:
                    return 1
            except TypeError:
                return 1
            return sum(map(basic_size, x))
        return basic_size(self.to_basic(template))

    def strictly_simpler(self, x, y):
        """
        Is the left hand argument *strictly* simpler than the right hand side.

        Required properties:

        1. not strictly_simpler(x, y)
        2. not (strictly_simpler(x, y) and strictly_simpler(y, x))
        3. not (strictly_simpler(x, y) and strictly_simpler(y, z)
           and strictly_simpler(z x))

        This is used for hinting in certain cases. The default implementation
        of it always returns False and this is perfectly acceptable to leave
        as is.
        """
        return False

    def simplifiers(self, random, template):
        """Yield a sequence of functions which each take a Random object and a
        single template and produce a generator over "simpler" versions of that
        template.

        The only other required invariant that each simplifier must satisfy is
        it should not be the case that strictly_simpler(x, y) for any y in
        simplify(random, x). That is, it's OK if the simplify doesn't produce
        a strictly simpler value but it must not produce a strictly more
        complex one.

        General tips for a good simplify function:

            1. The generator shouldn't yield too many values. A few hundred is
               fine, but if you're generating millions of simplifications you
               may wish to reconsider your life choices and evaluate which ones
               actually matter to you.
            2. Cycles in simplify are fine, but the simplify graph should be
               bounded in the sense that there should be no infinite acyclic
               paths where a1 simplifies to a2 simplifies to ...
            3. Try major simplifications first to see if you get lucky. Yield
               a minimal element, throw out half of your data, etc. Providing
               shortcuts in the graph will speed up the simplification process
               a lot.

        The template argument is provided to allow picking simplifiers that are
        likely to be useful. It should be considered only a hint, and each
        simplifier must be valid (in the sense of not erroring. It doesn't have
        to do anything useful) for all templates valid for this strategy.

        By default this just yields the basic_simplify function (which in turn
        by default does not do anything useful). If you override this function
        and also override basic_simplify you should make sure to yield it, or
        it will not be called.

        """
        yield self.basic_simplify

    def full_simplify(self, random, template):
        """A convenience method.

        Run each simplifier over this template and yield the results in
        turn.

        The order in which simplifiers are run is lightly randomized from the
        order in which simplifiers provides them, in order to avoid certain
        pathological cases.

        """
        saved_for_later = []
        for simplifier in self.simplifiers(random, template):
            if random.randint(0, 1):
                for value in simplifier(random, template):
                    yield value
            else:
                saved_for_later.append(simplifier)
        random.shuffle(saved_for_later)
        for simplifier in saved_for_later:
            for value in simplifier(random, template):
                yield value

    def basic_simplify(self, random, template):
        """A convenience method for subclasses that do not have complex
        simplification requirements to override.

        See simplifiers for details.

        """
        return iter(())


class OneOfStrategy(SearchStrategy):

    """Implements a union of strategies. Given a number of strategies this
    generates values which could have come from any of them.

    The conditional distribution draws uniformly at random from some non-empty
    subset of these strategies and then draws from the conditional distribution
    of that strategy.

    """

    Parameter = namedtuple(
        'Parameter', ('chooser', 'child_parameters')
    )

    def __init__(self,
                 strategies):
        SearchStrategy.__init__(self)
        strategies = tuple(strategies)
        if len(strategies) <= 1:
            raise ValueError('Need at least 2 strategies to choose amongst')
        self.element_strategies = list(strategies)
        self.template_upper_bound = 0
        for e in self.element_strategies:
            self.template_upper_bound += e.template_upper_bound
        self.template_upper_bound = infinitish(self.template_upper_bound)

    def __repr__(self):
        return ' | '.join(map(repr, self.element_strategies))

    def strictly_simpler(self, x, y):
        lx, vx = x
        ly, vy = y
        if lx < ly:
            return True
        if lx > ly:
            return False
        return self.element_strategies[lx].strictly_simpler(vx, vy)

    def reify(self, value):
        s, x = value
        return self.element_strategies[s].reify(x)

    def draw_parameter(self, random):
        n = len(self.element_strategies)
        return self.Parameter(
            chooser=chooser(
                random.getrandbits(8) + 1 for _ in hrange(n)),
            child_parameters=[
                s.draw_parameter(random) for s in self.element_strategies]
        )

    def draw_template(self, random, pv):
        child = pv.chooser.choose(random)
        return (
            child,
            self.element_strategies[child].draw_template(
                random, pv.child_parameters[child]))

    def element_simplifier(self, s, simplifier):
        def accept(random, template):
            if template[0] != s:
                return
            for value in simplifier(random, template[1]):
                yield (s, value)
        accept.__name__ = str(
            'element_simplifier(%d, %s)' % (
                s, simplifier.__name__,
            )
        )
        return accept

    def simplifiers(self, random, template):
        i, value = template
        for j in hrange(i):
            yield self.redraw_simplifier(j)

        for simplify in self.element_strategies[i].simplifiers(random, value):
            yield self.element_simplifier(i, simplify)

    def redraw_simplifier(self, child):
        def accept(random, template):
            i, value = template
            if child >= i:
                return
            for _ in hrange(20):
                redraw = self.element_strategies[child].draw_and_produce(
                    random)
                yield child, redraw
        accept.__name__ = str(
            'redraw_simplifier(%d)' % (child,))
        return accept

    def to_basic(self, template):
        i, value = template
        return [i, self.element_strategies[i].to_basic(value)]

    def from_basic(self, data):
        check_data_type(list, data)
        check_length(2, data)
        i, value = data
        check_data_type(integer_types, i)
        if i < 0:
            raise BadData('Index out of range: %d < 0' % (i,))
        elif i >= len(self.element_strategies):
            raise BadData(
                'Index out of range: %d >= %d' % (
                    i, len(self.element_strategies)))

        return (i, self.element_strategies[i].from_basic(value))


class MappedSearchStrategy(SearchStrategy):

    """A strategy which is defined purely by conversion to and from another
    strategy.

    Its parameter and distribution come from that other strategy.

    """

    def __init__(self, strategy, pack=None):
        SearchStrategy.__init__(self)
        self.mapped_strategy = strategy
        self.template_upper_bound = self.mapped_strategy.template_upper_bound
        if pack is not None:
            self.pack = pack

    def __repr__(self):
        return 'MappedSearchStrategy(%r, %s)' % (
            self.mapped_strategy, getattr(
                self.pack, '__name__', type(self.pack).__name__))

    def draw_parameter(self, random):
        return self.mapped_strategy.draw_parameter(random)

    def draw_template(self, random, pv):
        return self.mapped_strategy.draw_template(random, pv)

    def pack(self, x):
        """Take a value produced by the underlying mapped_strategy and turn it
        into a value suitable for outputting from this strategy."""
        raise NotImplementedError(
            '%s.pack()' % (self.__class__.__name__))

    def reify(self, value):
        return self.pack(self.mapped_strategy.reify(value))

    def simplifiers(self, random, template):
        return self.mapped_strategy.simplifiers(random, template)

    def strictly_simpler(self, x, y):
        return self.mapped_strategy.strictly_simpler(x, y)

    def to_basic(self, template):
        return self.mapped_strategy.to_basic(template)

    def from_basic(self, data):
        return self.mapped_strategy.from_basic(data)


class FilteredStrategy(MappedSearchStrategy):

    def __init__(self, strategy, condition):
        super(FilteredStrategy, self).__init__(strategy=strategy)
        self.condition = condition

    def pack(self, value):
        assume(self.condition(value))
        return value


def tupleize(data):
    if isinstance(data, list):
        return tuple(map(tupleize, data))
    else:
        return data


class FlatMapTemplate(object):

    def __init__(
        self,
        source_template, target_parameter_seed, target_template_seed,
        target_data=not_set, last_strategy=not_set,
    ):
        self.source_template = source_template
        self.target_parameter_seed = target_parameter_seed
        self.target_template_seed = target_template_seed
        self.target_data = target_data
        self.last_strategy = last_strategy
        trace = [source_template, target_parameter_seed, target_template_seed]
        if target_data != not_set:
            trace.append(tupleize(target_data))
        self.trace = tuple(trace)

    def __trackas__(self):
        result = [
            self.source_template, self.target_parameter_seed,
            self.target_template_seed,
        ]
        if self.target_data != not_set:
            result.append(self.target_data)
        return result

    def __eq__(self, other):
        return isinstance(other, FlatMapTemplate) and (
            self.trace == other.trace
        )

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(self.trace)


class FlatMapStrategy(SearchStrategy):

    def __init__(
        self, strategy, expand
    ):
        self.flatmapped_strategy = strategy
        self.expand = expand
        self.settings = Settings.default

    def __repr__(self):
        return 'FlatMapStrategy(%r, %s)' % (
            self.flatmapped_strategy, getattr(
                self.expand, '__name__', type(self.expand).__name__))

    def draw_parameter(self, random):
        return (
            self.flatmapped_strategy.draw_parameter(random),
            random.getrandbits(64),
        )

    def strictly_simpler(self, x, y):
        if self.flatmapped_strategy.strictly_simpler(
            x.source_template, y.source_template
        ):
            return True
        if self.flatmapped_strategy.strictly_simpler(
            y.source_template, x.source_template
        ):
            return False
        return x.target_template_seed < y.target_template_seed

    def draw_template(self, random, parameter):
        source_parameter, parameter_seed = parameter
        source_template = self.flatmapped_strategy.draw_template(
            random, source_parameter)
        template_seed = random.getrandbits(64)
        return FlatMapTemplate(
            source_template=source_template,
            target_parameter_seed=parameter_seed,
            target_template_seed=template_seed,
        )

    def reify(self, template):
        source = self.flatmapped_strategy.reify(template.source_template)
        target_strategy = strategy(self.expand(source), self.settings)
        template.last_strategy = target_strategy
        target_template = not_set
        if template.target_data != not_set:
            try:
                target_template = target_strategy.from_basic(
                    template.target_data)
            except BadData:
                template.target_data = not_set
                pass
        if template.target_data == not_set:
            target_template = target_strategy.draw_template(
                Random(template.target_template_seed),
                target_strategy.draw_parameter(Random(
                    template.target_parameter_seed))
            )
        template.target_data = target_strategy.to_basic(target_template)
        return target_strategy.reify(target_template)

    def simplifiers(self, random, template):
        for simplify in self.flatmapped_strategy.simplifiers(
            random, template.source_template
        ):
            yield self.left_simplifier(simplify)
        if template.last_strategy != not_set:
            try:
                target_template = template.last_strategy.from_basic(
                    template.target_data
                )
            except BadData:
                return
            for simplify in template.last_strategy.simplifiers(
                random, target_template
            ):
                yield self.right_simplifier(simplify, template.last_strategy)

    def left_simplifier(self, simplify):
        def accept(random, template):
            for new_source_template in simplify(
                random, template.source_template
            ):
                yield FlatMapTemplate(
                    source_template=new_source_template,
                    target_parameter_seed=template.target_parameter_seed,
                    target_template_seed=template.target_template_seed,
                )
        accept.__name__ = str(
            'left(%s)' % (simplify.__name__,)
        )
        return accept

    def right_simplifier(self, simplify, target_strategy):
        def accept(random, template):
            try:
                target_template = target_strategy.from_basic(
                    template.target_data)
            except BadData:
                template.target_data = not_set
                return
            for new_target_template in simplify(random, target_template):
                new_target_data = target_strategy.to_basic(new_target_template)
                yield FlatMapTemplate(
                    source_template=template.source_template,
                    target_parameter_seed=template.target_parameter_seed,
                    target_template_seed=template.target_template_seed,
                    target_data=new_target_data,
                )
        accept.__name__ = str(
            'right(%s)' % (simplify.__name__,)
        )
        return accept

    def to_basic(self, template):
        start = [
            self.flatmapped_strategy.to_basic(template.source_template),
            template.target_parameter_seed, template.target_template_seed
        ]
        if template.target_data != not_set:
            start.append(template.target_data)
        return start

    def from_basic(self, data):
        check_data_type(list, data)
        if len(data) < 3:
            raise BadData('Expected at least 3 elements but got %d' % (
                len(data),
            ))
        if len(data) > 4:
            raise BadData('Expected at most 4 elements but got %d' % (
                len(data),
            ))
        check_data_type(integer_types, data[1])
        check_data_type(integer_types, data[2])
        target_data = data[-1] if len(data) == 4 else not_set
        return FlatMapTemplate(
            self.flatmapped_strategy.from_basic(data[0]),
            target_data=target_data,
            target_parameter_seed=data[1],
            target_template_seed=data[2],
        )
