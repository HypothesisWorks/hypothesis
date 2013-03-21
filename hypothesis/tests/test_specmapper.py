from hypothesis.specmapper import SpecificationMapper, MissingSpecification
import pytest

def setup_function(fn):
    SpecificationMapper.default_mapper = None
    fn()

def test_can_define_specifications():
    sm = SpecificationMapper()
    sm.define_specification_for("foo", 1)
    assert sm.specification_for("foo") == 1

def test_can_define_specifications_on_the_default():
    sm = SpecificationMapper()
    SpecificationMapper.default().define_specification_for("foo", 1)
    assert sm.specification_for("foo") == 1

class Bar:
    pass

def test_can_define_specifications_for_classes():
    sm = SpecificationMapper()
    sm.define_specification_for(Bar, 1)
    assert sm.specification_for(Bar) == 1
    
def test_can_define_specifications_for_built_in_types():
    sm = SpecificationMapper()
    sm.define_specification_for(Bar, 1)
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
