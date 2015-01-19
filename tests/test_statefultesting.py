from hypothesis.statefultesting import (
    StatefulTest,
    step,
    requires,
    precondition,
    integrity_test,
    TestRun,
    Step,
)
import pytest
from hypothesis import Unfalsifiable
from hypothesis.database.converter import ConverterTable, WrongFormat
from hypothesis.internal.compat import hrange
from hypothesis import falsify


class Foo(StatefulTest):

    @integrity_test
    def are_you_still_there(self):
        assert True

    @step
    def blargh(self):
        pass

    def bar(self):
        pass  # pragma: no cover

    @step
    def baz(self):
        pass


def test_picks_up_only_annotated_methods_as_operations():
    assert len(Foo.test_steps()) == 2
    assert len(Foo.integrity_tests()) == 1


def test_raises_on_no_example():
    with pytest.raises(Unfalsifiable):
        Foo.breaking_example()


class BrokenCounter(StatefulTest):

    def __init__(self):
        self.value = 0

    @step
    def inc(self):
        start_value = self.value
        self.value += 1
        assert self.value == start_value + 1

    @step
    def dec(self):
        precondition(self.value > 0)
        start_value = self.value
        if(self.value != 5):
            self.value -= 1
        assert self.value == start_value - 1




def test_finds_broken_example():
    assert [x[0]
            for x in BrokenCounter.breaking_example()] == ['inc'] * 5 + ['dec']


class AlwaysBroken(StatefulTest):

    @step
    def do_something(self):
        pass

    @integrity_test
    def go_boom(self):
        assert False


def test_runs_integrity_checks_initially():
    assert len(AlwaysBroken.breaking_example()) == 0


class SubclassAlwaysBroken(AlwaysBroken):
    pass


class SubclassBrokenCounter(BrokenCounter):
    pass


def test_subclassing_tests_inherits_steps_and_checks():
    SubclassAlwaysBroken.breaking_example()
    SubclassBrokenCounter.breaking_example()


class QuicklyBroken(StatefulTest):

    def __init__(self):
        self.value = 0

    @step
    def inc(self):
        self.value += 1

    @integrity_test
    def is_small(self):
        assert self.value < 2


def test_runs_integrity_checks_after_each_step():
    assert len(QuicklyBroken.breaking_example()) == 2


class NumberHater(StatefulTest):

    @requires(int)
    @step
    def hates_fives(self, n):
        assert n < self.hated_number


class FiveHater(NumberHater):
    hated_number = 5


class EightHater(NumberHater):
    hated_number = 8


def test_minimizes_arguments_to_steps():
    steps = FiveHater.breaking_example()
    assert len(steps) == 1
    assert steps[0][1] == 5

    steps = EightHater.breaking_example()
    assert len(steps) == 1
    assert steps[0][1] == 8


class BadSet(object):

    def __init__(self):
        self.data = []

    def add(self, arg):
        self.data.append(arg)

    def remove(self, arg):
        for i in hrange(0, len(self.data)):
            if self.data[i] == arg:
                del self.data[i]
                break

    def contains(self, arg):
        return arg in self.data

    def clear(self):
        self.data = []


class BadSetTester(StatefulTest):

    def __init__(self):
        self.target = BadSet()

    @step
    @requires(int)
    def add(self, i):
        self.target.add(i)
        assert self.target.contains(i)

    @step
    @requires(int)
    def remove(self, i):
        self.target.remove(i)
        assert not self.target.contains(i)

    @step
    def clear(self):
        self.target.clear()


def test_bad_set_finds_minimal_break():
    breaking_example = BadSetTester.breaking_example()
    assert len(breaking_example) == 3
    assert len(set([s[1] for s in breaking_example])) == 1


class NeedsKeywordArgs(StatefulTest):

    @step
    @requires(x=int)
    def do_stuff(self, x):
        assert x > 0


def test_passes_keyword_args():
    example = NeedsKeywordArgs.breaking_example()
    assert example == [('do_stuff', 0)]


class RequiresInit(StatefulTest):

    @requires(bool)
    def __init__(self, x):
        self.x = x

    @step
    def assert_self(self):
        assert self.x


def test_can_generate_for_init():
    example = RequiresInit.breaking_example()
    assert example == [('__init__', False), ('assert_self',)]


def test_init_args_appear_in_repr():
    tr = TestRun(RequiresInit, init_args=(), init_kwargs={'x': 42}, steps=[])
    assert '42' in repr(tr)


class HasOneBreakingMethod(StatefulTest):

    @step
    def all_good(self):
        pass

    @step
    def not_so_good(self):
        assert False


def test_prune_immediately_removes_every_thing_after_a_bad_call():
    tr = TestRun(HasOneBreakingMethod, steps=(
        [Step(HasOneBreakingMethod.all_good, (), {})] * 10 +
        [Step(HasOneBreakingMethod.not_so_good, (), {})] * 10 +
        [Step(HasOneBreakingMethod.all_good, (), {})] * 10
    ))
    pruned = tr.prune()
    assert len(pruned.steps) == 11
    assert pruned.steps[-1].target == HasOneBreakingMethod.not_so_good


class IsPickyAboutPreconditions(StatefulTest):

    def __init__(self):
        self.lefts = 0
        self.rights = 0

    @step
    def left(self):
        precondition(self.rights >= self.lefts)
        self.lefts += 1

    @step
    def right(self):
        precondition(self.lefts >= self.rights)
        self.rights += 1
        assert self.rights < 3


def test_can_find_a_breaking_example_with_lots_of_preconditions():
    assert len(IsPickyAboutPreconditions.breaking_example()) == 5


class IsBadAndShouldFeelBad(StatefulTest):
    @step
    def bad(self):
        assert False


class IsBadButItsNotMyFault(StatefulTest):
    @step
    def bad(self):
        assert False


def test_cannot_save_an_example_in_the_wrong_format():
    example = falsify(TestRun.run, IsBadAndShouldFeelBad)[0]
    converter = ConverterTable.default().specification_for(
        IsBadButItsNotMyFault)
    with pytest.raises(WrongFormat):
        converter.to_json(example)
