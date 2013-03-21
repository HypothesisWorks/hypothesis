class SpecificationMapper:
    @classmethod
    def default(cls):
        try:
            if cls.default_mapper:
                return cls.default_mapper
        except AttributeError:
            pass
        cls.default_mapper = cls()
        return cls.default_mapper

    def __init__(self):
        self.value_mappers = {}
        self.instance_mappers = {}
    
    def define_specification_for(self, value, specification):
        self.value_mappers[value] = specification

    def define_specification_for_instances(self, cls, specification_builder):
        self.instance_mappers[cls] = specification_builder

    def specification_for(self, descriptor, originating_mapper=None):
        originating_mapper = originating_mapper or self
        cls = descriptor.__class__
        if descriptor in self.value_mappers:
            return self.value_mappers[descriptor]
        elif cls in self.instance_mappers:
            return self.instance_mappers[cls](originating_mapper, descriptor)
        elif self is self.default():
            return originating_mapper.missing_specification(descriptor)
        else:
            return self.default().specification_for(descriptor, originating_mapper = self)

    def missing_specification(self, spec):
        raise MissingSpecification(self, descriptor)

class MissingSpecification(Exception):
    def __init__(self, descriptor):
        Exception.__init__(self, "Unable to produce specification for descriptor %s" % str(descriptor))
