from hypothesis.internal.specmapper import (
    SpecificationMapper,
    MissingSpecification,
    next_in_chain,
    sort_in_subclass_order,
)
from hypothesis import given
from hypothesis.descriptors import sampled_from
import pytest
from collections import namedtuple
import random
from hypothesis.internal.compat import xrange


def setup_function(fn):
    SpecificationMapper.default_mapper = None
    fn()


def const(x):
    return lambda *args: x


def test_can_define_specifications():
    sm = SpecificationMapper()
    sm.define_specification_for('foo', const(1))
    assert sm.specification_for('foo') == 1


def test_can_define_specifications_on_the_default():
    sm = SpecificationMapper()
    SpecificationMapper.default().define_specification_for('foo', const(1))
    assert sm.specification_for('foo') == 1


class Bar(object):
    pass


def test_can_define_specifications_for_classes():
    sm = SpecificationMapper()
    sm.define_specification_for(Bar, const(1))
    assert sm.specification_for(Bar) == 1


def test_can_define_specifications_for_built_in_types():
    sm = SpecificationMapper()
    sm.define_specification_for(Bar, const(1))
    assert sm.specification_for(Bar) == 1


def test_can_define_instance_specifications():
    sm = SpecificationMapper()
    sm.define_specification_for_instances(str, lambda _, i: i + 'bar')
    assert sm.specification_for('foo') == 'foobar'


def test_can_define_instance_specifications_on_the_default():
    sm = SpecificationMapper()
    SpecificationMapper.default().define_specification_for_instances(
        str,
        lambda _, i: i + 'bar'
    )
    assert sm.specification_for('foo') == 'foobar'


def test_can_define_instance_specifications_for_lists():
    sm = SpecificationMapper()
    sm.define_specification_for_instances(list, lambda _, l: len(l))
    assert sm.specification_for([1, 2]) == 2


def test_raises_missing_specification_with_no_spec():
    sm = SpecificationMapper()
    with pytest.raises(MissingSpecification):
        sm.specification_for('hi')


def test_can_create_children():
    sm = SpecificationMapper()
    child = sm.new_child_mapper()
    sm.define_specification_for('foo', const(1))
    assert child.specification_for('foo') == 1


def test_can_override_in_children():
    sm = SpecificationMapper()
    child = sm.new_child_mapper()
    sm.define_specification_for('foo', const(1))
    child.define_specification_for('foo', const(2))
    assert sm.specification_for('foo') == 1
    assert child.specification_for('foo') == 2


class ChildMapper(SpecificationMapper):
    pass


def test_does_not_inherit_default():
    assert ChildMapper.default() != SpecificationMapper.default()
    SpecificationMapper.default().define_specification_for('foo', const(1))
    with pytest.raises(MissingSpecification):
        ChildMapper.default().specification_for('foo')


def test_can_call_other_specs():
    s = SpecificationMapper()
    s.define_specification_for('foo', const(1))
    s.define_specification_for(
        'bar',
        lambda t, _: t.specification_for('foo') + 1
    )
    assert s.specification_for('bar') == 2


def test_child_can_call_other_specs_on_prototype():
    s = SpecificationMapper()
    s.define_specification_for(
        'bar',
        lambda t, d: t.specification_for('foo') + 1
    )
    s2 = s.new_child_mapper()
    s2.define_specification_for('foo', const(1))
    assert s2.specification_for('bar') == 2


def test_can_override_specifications():
    s = SpecificationMapper()
    s.define_specification_for('foo', const(1))
    s.define_specification_for('foo', const(2))
    assert s.specification_for('foo') == 2


def test_can_override_instance_specifications():
    s = SpecificationMapper()
    s.define_specification_for_instances(str, const(1))
    s.define_specification_for_instances(str, const(2))
    assert s.specification_for('foo') == 2


def test_can_call_previous_in_overridden_specifications():
    s = SpecificationMapper()
    s.define_specification_for_instances(str, lambda _, s: len(s))
    s.define_specification_for_instances(
        str,
        lambda _, s: 5 if len(s) > 5 else next_in_chain()
    )
    assert s.specification_for('foo') == 3
    assert s.specification_for(
        'I am the very model of a modern major general'
    ) == 5


class Foo(object):
    pass


class Fooc(Foo):
    pass


class Baz(object):
    pass


def test_can_define_class_specifications():
    s = SpecificationMapper()
    s.define_specification_for_classes(lambda _, c: c())
    assert s.specification_for(Foo).__class__ == Foo


def test_can_define_class_specifications_for_subclasses():
    s = SpecificationMapper()
    s.define_specification_for_classes(const(1))
    s.define_specification_for_classes(const(2), subclasses_of=Foo)
    assert s.specification_for(Foo) == 2
    assert s.specification_for(Fooc) == 2
    assert s.specification_for(Baz) == 1


def test_multiple_calls_return_same_value():
    s = SpecificationMapper()
    s.define_specification_for_instances(str, lambda *_: Foo())

    assert s.specification_for('foo') is s.specification_for('foo')
    assert s.specification_for('foo') is not s.specification_for('bar')


def test_defining_new_handlers_resets_cache():
    s = SpecificationMapper()
    s.define_specification_for_instances(str, lambda *_: Foo())
    x = s.specification_for('foo')
    s.define_specification_for_instances(str, lambda *_: Fooc())
    y = s.specification_for('foo')
    assert y is not x
    assert isinstance(y, Fooc)


def test_cache_correctly_handles_inheritance():
    s = SpecificationMapper()
    s.define_specification_for_instances(
        list,
        lambda s, d: [s.specification_for(d[0])]
    )
    t = s.new_child_mapper()
    t.define_specification_for_instances(str, lambda *_: Foo())

    x = t.specification_for('foo')
    y = t.specification_for(['foo'])[0]
    assert x is y


Litter = namedtuple('Litter', ('kitten1', 'kitten2'))


def test_can_handle_subtypes_of_instances():
    s = SpecificationMapper()
    s.define_specification_for_instances(tuple, lambda s, d: sum(d))

    assert s.specification_for((1, 2)) == 3
    assert s.specification_for(Litter(2, 2)) == 4


def test_can_override_handlers_for_supertypes():
    s = SpecificationMapper()
    s.define_specification_for_instances(tuple, lambda s, d: sum(d))
    s.define_specification_for_instances(Litter, lambda s, d: len(d))

    assert s.specification_for((1, 2)) == 3
    assert s.specification_for(Litter(2, 2)) == 2


def test_can_handle_large_numbers_of_instance_mappers():
    def f(s, x):
        return str(x)

    s = SpecificationMapper()
    s.define_specification_for_instances(tuple, f)
    s.define_specification_for_instances(Litter, f)
    s.define_specification_for_instances(list, f)
    s.define_specification_for_instances(set, f)
    s.define_specification_for_instances(str, f)
    s.define_specification_for_instances(int, f)

    assert s.specification_for((1, 1)) == '(1, 1)'


def test_invokes_missing_if_all_handlers_defer():
    s = SpecificationMapper()
    s.define_specification_for(int, lambda ss, d: next_in_chain())
    s.missing_specification = lambda d: 11
    assert s.specification_for(int) == 11


class Parent(object):
    pass


class Child(Parent):
    pass


class Grandchild(Child):
    pass


class GreatGrandchild(Grandchild):
    pass


def test_specifications_will_match_on_subclasses():
    s = SpecificationMapper()

    def trivial(x):
        return lambda s, d: x

    s.define_specification_for_instances(Parent, trivial(1))
    assert s.specification_for(Parent()) == 1
    assert s.specification_for(Child()) == 1
    assert s.specification_for(Grandchild()) == 1
    assert s.specification_for(GreatGrandchild()) == 1

    s.define_specification_for_instances(Grandchild, trivial(2))
    assert s.specification_for(Parent()) == 1
    assert s.specification_for(Child()) == 1
    assert s.specification_for(Grandchild()) == 2
    assert s.specification_for(GreatGrandchild()) == 2

    s.define_specification_for_instances(Child, trivial(3))
    assert s.specification_for(Parent()) == 1
    assert s.specification_for(Child()) == 3
    assert s.specification_for(Grandchild()) == 2
    assert s.specification_for(GreatGrandchild()) == 2

    s.define_specification_for_instances(GreatGrandchild, trivial(4))
    assert s.specification_for(Parent()) == 1
    assert s.specification_for(Child()) == 3
    assert s.specification_for(Grandchild()) == 2
    assert s.specification_for(GreatGrandchild()) == 4

    choices = [Parent, Child, Grandchild, GreatGrandchild]
    values = {
        Parent: 1, Child: 3, Grandchild: 2, GreatGrandchild: 4
    }

    for i in xrange(5, 200):
        c = random.choice(choices)
        assert s.specification_for(c()) == values[c]
        s.define_specification_for_instances(c, trivial(i))
        assert s.specification_for(c()) == i
        values[c] = i


class A(object):
    pass


class AA(A):
    pass


class AAA(AA):
    pass


class AAB(AA):
    pass


class AB(A):
    pass


class ABA(AB):
    pass


class ABB(AB):
    pass


class B(object):
    pass


class BA(B):
    pass


class BAA(BA):
    pass


class BAB(BA):
    pass


class BB(B):
    pass


class BBA(BB):
    pass


class BBB(AB):
    pass


all_test_classes = [
    A, AA, AAA, AAB, AB, ABA, ABB,
    B, BA, BAA, BAB, BB, BBA, BBB
]


def find_most_specific(x, classes):
    best = None
    for c in classes:
        if isinstance(x, c):
            if best is None or issubclass(c, best):
                best = c
    return best


@given({sampled_from(all_test_classes)}, random.Random)
def test_chooses_most_specific_subclass(classes, r):
    classes = list(classes)
    random.shuffle(classes)
    classes = tuple(classes)
    mapper = SpecificationMapper()
    for i in xrange(len(classes)):
        mapper.define_specification_for_instances(
            classes[i],
            const(i),
        )
    for c in all_test_classes:
        if issubclass(c, classes):
            x = c()
            correct_choice = find_most_specific(x, classes)
            i = mapper.specification_for(x)
            assert i == classes.index(correct_choice)


@given({sampled_from(all_test_classes)}, random.Random)
def test_class_sorter_topologically_sorts_wrt_subclassing(classes, random):
    classes = list(classes)
    random.shuffle(classes)
    in_order = sort_in_subclass_order(classes)
    n = len(classes)
    for i in xrange(n):
        for j in xrange(i+1, n):
            assert not issubclass(in_order[j], in_order[i])


def test_correctly_reports_specifications():
    mapper = SpecificationMapper()
    mapper.define_specification_for_instances(
        list,
        lambda s, d: s.specification_for(d[0]) + 1 if d else 0
    )
    mapper.define_specification_for(int, const(1))
    assert mapper.has_specification_for(int)
    assert mapper.has_specification_for([int])
    assert mapper.has_specification_for([])
    assert not mapper.has_specification_for(str)
    assert not mapper.has_specification_for([str])
