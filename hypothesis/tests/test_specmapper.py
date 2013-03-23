from hypothesis.specmapper import SpecificationMapper, MissingSpecification, next_in_chain
import pytest

def setup_function(fn):
    SpecificationMapper.default_mapper = None
    fn()

def const(x): return lambda *args: x

def test_can_define_specifications():
    sm = SpecificationMapper()
    sm.define_specification_for("foo", const(1))
    assert sm.specification_for("foo") == 1

def test_can_define_specifications_on_the_default():
    sm = SpecificationMapper()
    SpecificationMapper.default().define_specification_for("foo", const(1))
    assert sm.specification_for("foo") == 1

class Bar:
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
    sm.define_specification_for_instances(str, lambda _, i: i + "bar")
    assert sm.specification_for("foo") == "foobar"

def test_can_define_instance_specifications_on_the_default():
    sm = SpecificationMapper()
    SpecificationMapper.default().define_specification_for_instances(str, lambda _, i: i + "bar")
    assert sm.specification_for("foo") == "foobar"

def test_can_define_instance_specifications_for_lists():
    sm = SpecificationMapper()
    sm.define_specification_for_instances(list, lambda _, l: len(l))
    assert sm.specification_for([1,2]) == 2

def test_raises_missing_specification_with_no_spec():
    sm = SpecificationMapper()
    with pytest.raises(MissingSpecification):
        sm.specification_for("hi")

def test_can_create_children():
    sm = SpecificationMapper()
    child = sm.new_child_mapper()
    sm.define_specification_for("foo", const(1))
    assert child.specification_for("foo") == 1

def test_can_override_in_children():
    sm = SpecificationMapper()
    child = sm.new_child_mapper()
    sm.define_specification_for("foo", const(1))
    child.define_specification_for("foo", const(2))

    assert sm.specification_for("foo") == 1
    assert child.specification_for("foo") == 2

class ChildMapper(SpecificationMapper):
  pass

def test_does_not_inherit_default():
  assert ChildMapper.default() != SpecificationMapper.default()
  SpecificationMapper.default().define_specification_for("foo", const(1))
  with pytest.raises(MissingSpecification):
    ChildMapper.default().specification_for("foo")

def test_can_call_other_specs():
    s = SpecificationMapper()
    s.define_specification_for("foo", const(1))
    s.define_specification_for("bar", lambda t, _: t.specification_for("foo") + 1)
    assert s.specification_for("bar") == 2
    
def test_child_can_call_other_specs_on_prototype():
    s = SpecificationMapper()
    s.define_specification_for("bar", lambda t, d: t.specification_for("foo") + 1)
    s2 = s.new_child_mapper()
    s2.define_specification_for("foo", const(1))
    assert s2.specification_for("bar") == 2

def test_can_override_specifications():
    s = SpecificationMapper()
    s.define_specification_for("foo", const(1))
    s.define_specification_for("foo", const(2))
    assert s.specification_for("foo") == 2

def test_can_override_instance_specifications():
    s = SpecificationMapper()
    s.define_specification_for_instances(str, const(1))
    s.define_specification_for_instances(str, const(2))
    assert s.specification_for("foo") == 2

def test_can_call_previous_in_overridden_specifications():
    s = SpecificationMapper()
    s.define_specification_for_instances(str, lambda _, s: len(s))
    s.define_specification_for_instances(str, lambda _, s: 5 if len(s) > 5 else next_in_chain())
    assert s.specification_for("foo") == 3
    assert s.specification_for("I am the very model of a modern major general") == 5

class Foo:
    pass

class Bar(Foo):
    pass

class Baz:
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
    assert s.specification_for(Bar) == 2
    assert s.specification_for(Baz) == 1

