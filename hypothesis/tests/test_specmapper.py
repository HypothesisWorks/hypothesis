from hypothesis.specmapper import SpecificationMapper

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

def test_can_define_instance_specifications():
    sm = SpecificationMapper()
    sm.define_specification_for_instances(str, lambda _, i: i + "bar")
    assert sm.specification_for("foo") == "foobar"

def test_can_define_instance_specifications_on_the_default():
    sm = SpecificationMapper()
    SpecificationMapper.default().define_specification_for_instances(str, lambda _, i: i + "bar")
    assert sm.specification_for("foo") == "foobar"
