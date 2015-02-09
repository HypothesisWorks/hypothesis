# coding=utf-8

# Copyright (C) 2013-2015 David R. MacIver (david@drmaciver.com)

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

from __future__ import division, print_function, unicode_literals

from inspect import getmembers
from collections import namedtuple

import hypothesis
from hypothesis.strategytable import StrategyTable
from hypothesis.searchstrategy import MappedSearchStrategy, \
    one_of_strategies
from hypothesis.internal.compat import hrange
from hypothesis.database.converter import Converter, WrongFormat, \
    ConverterTable, check_type
from hypothesis.internal.utils.reflection import convert_keyword_arguments


def step(f):
    f.hypothesis_test_step = True

    if not hasattr(f, 'hypothesis_test_requirements'):
        f.hypothesis_test_requirements = ((), {})
    return f


def integrity_test(f):
    f.hypothesis_integrity_tests = True
    return f


def requires(*args, **kwargs):
    def alter_function(f):
        f.hypothesis_test_requirements = (args, kwargs)
        return f
    return alter_function


class PreconditionNotMet(Exception):

    def __init__(self):
        Exception.__init__(self, 'Precondition not met')


def precondition(t):
    if not t:
        raise PreconditionNotMet()


class TestRun(object):

    def __init__(self, cls, steps, init_args=None, init_kwargs=None):
        self.cls = cls
        self.init_args = tuple(init_args or ())
        self.init_kwargs = dict(init_kwargs or {})
        self.steps = steps
        assert all(s.target.__name__ != '__init__' for s in steps)
        self.steps = steps

    def __repr__(self):
        return 'TestRun(%s, init_args=%r, init_kwargs=%r, steps=%r)' % (
            self.cls.__name__,
            self.init_args,
            self.init_kwargs,
            self.steps,
        )

    def new_value(self):
        return self.cls(*self.init_args, **self.init_kwargs)

    def run(self):
        tests = self.cls.integrity_tests()

        value = self.new_value()

        def run_integrity_tests():
            for t in tests:
                t(value)
        run_integrity_tests()
        for s, args, kwargs in self.steps:
            try:
                s(value, *args, **kwargs)
                run_integrity_tests()
            except PreconditionNotMet:
                pass
        return True

    def prune(self):
        results = []
        v = self.new_value()
        for s in self.steps:
            try:
                s[0](v, *s[1])
                results.append(s)
            except PreconditionNotMet:
                continue
            except Exception:  # pylint: disable=broad-except
                results.append(s)
                break
        if len(results) == len(self):
            return None
        else:
            return TestRun(
                self.cls, results,
                init_args=self.init_args,
                init_kwargs=self.init_kwargs,
            )

    def __len__(self):
        if self.init_args or self.init_kwargs:
            return 1 + len(self.steps)
        else:
            return len(self.steps)

    def __iter__(self):
        if self.init_args or self.init_kwargs:
            yield Step(self.cls.__init__, self.init_args, self.init_kwargs)
        for s in self.steps:
            yield s


class StatefulTest(object):

    @classmethod
    def test_steps(cls):
        return cls.functions_with_attributes('hypothesis_test_step')

    @classmethod
    def integrity_tests(cls):
        return cls.functions_with_attributes('hypothesis_integrity_tests')

    @classmethod
    def functions_with_attributes(cls, attr):
        return [v for _, v in getmembers(cls) if hasattr(v, attr)]

    @classmethod
    def breaking_example(cls):
        test_run = hypothesis.falsify(TestRun.run, cls)[0]
        result = []
        for f, args, kwargs in test_run:
            args, kwargs = convert_keyword_arguments(f, (None,) + args, kwargs)
            args = args[1:]
            result.append((f.__name__,) + args)
        return result

Step = namedtuple('Step', ('target', 'arguments', 'kwargs'))


class StepStrategy(MappedSearchStrategy):

    def could_have_produced(self, x):
        # There's really no sensible way you could get here without this being
        # a Step because of how much this is an implementation detail
        assert isinstance(x, Step)  # pragma: no cover
        if x.target != self.descriptor:
            return False
        return self.mapped_strategy.could_have_produced(
            (x.arguments, x.kwargs))

    def pack(self, x):
        return Step(self.descriptor, x[0], x[1])

    def unpack(self, x):
        return (x.arguments, x.kwargs)


class StatefulConverter(Converter):

    def __init__(self, format_table, descriptor):
        Converter.__init__(self)
        self.descriptor = descriptor
        self.steps = tuple(descriptor.test_steps())
        self.formats = tuple(
            format_table.specification_for(s.hypothesis_test_requirements)
            for s in self.steps
        )
        self.init_format = format_table.specification_for(
            getattr(
                descriptor.__init__,
                'hypothesis_test_requirements',
                ((), {}),
            )
        )

    def to_basic(self, value):
        check_type(TestRun, value)
        if value.cls != self.descriptor:
            raise WrongFormat(
                'Tried to serialize a TestRun from %s as a TestRun from %s' % (
                    value.cls.__name__, self.descriptor.__name__
                ))
        init = self.init_format.to_basic((value.init_args, value.init_kwargs))
        steps = []
        for s in value.steps:
            i = self.steps.index(s.target)
            steps.append([
                s.target.__name__,
                self.formats[i].to_basic((s.arguments, s.kwargs))
            ])
        return [init, steps]

    def from_basic(self, data):
        init, steps = data
        init = self.init_format.from_basic(init)
        parsed_steps = []
        for name, data in steps:
            for i in hrange(len(self.steps)):  # pragma: no branch
                if self.steps[i].__name__ == name:
                    parsed_steps.append(
                        Step(self.steps[i], *self.formats[i].from_basic(data))
                    )
                    break
        return TestRun(
            cls=self.descriptor,
            steps=parsed_steps,
            init_args=init[0],
            init_kwargs=init[1],
        )


def define_stateful_strategy(strategies, descriptor):
    step_strategies = [
        StepStrategy(
            descriptor=s,
            strategy=strategies.strategy(s.hypothesis_test_requirements)
        )
        for s in descriptor.test_steps()
    ]
    try:
        init_requirements = (
            descriptor.__init__.hypothesis_test_requirements)
    except AttributeError:
        init_requirements = None
    requires_init = init_requirements is not None
    child_mapper = strategies.new_child_mapper()
    child_mapper.define_specification_for(
        Step,
        lambda sgs, _: sgs.strategy(one_of_strategies(step_strategies))
    )
    if requires_init:
        mapped_strategy = child_mapper.strategy((
            init_requirements, [Step]))
    else:
        mapped_strategy = child_mapper.strategy([Step])
    return StatefulStrategy(
        descriptor=descriptor, strategy=mapped_strategy,
        requires_init=requires_init
    )


class StatefulStrategy(MappedSearchStrategy):

    def __init__(self, descriptor, strategy, requires_init):
        super(StatefulStrategy, self).__init__(
            descriptor=descriptor, strategy=strategy
        )
        self.requires_init = requires_init

    def could_have_produced(self, value):
        return (
            isinstance(value, TestRun) and
            value.cls == self.descriptor
        )

    def pack(self, steps):
        if self.requires_init:
            (init_args, init_kwargs), steps = steps
            return TestRun(
                cls=self.descriptor,
                steps=steps,
                init_args=init_args,
                init_kwargs=init_kwargs
            )
        return TestRun(self.descriptor, steps)

    def unpack(self, x):
        steps = x.steps
        if self.requires_init:
            return ((x.init_args, x.init_kwargs), steps)
        else:
            return steps

    def simplify(self, x):
        pruned = x.prune()
        if pruned:
            yield pruned

        for y in super(StatefulStrategy, self).simplify(x):
            yield y

StrategyTable.default().define_specification_for_classes(
    define_stateful_strategy,
    subclasses_of=StatefulTest
)

ConverterTable.default().define_specification_for_classes(
    StatefulConverter,
    subclasses_of=StatefulTest
)
