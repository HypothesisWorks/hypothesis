class SpecificationMapper:
    """
    Maps descriptions of some type to a type. Has configurable handlers for what a description
    may look like. Handlers for descriptions may take either a specific value or all instances
    of a type and have access to the mapper to look up types.

    Also supports prototype based inheritance, with children being able to override specific handlers
    
    There is a single default() object per subclass of SpecificationMapper which everything has
    as a prototype if it's not assigned any other prototype. This allows you to easily define the
    mappers 
    """

    @classmethod
    def default(cls):
        try:
            if cls.default_mapper:
                return cls.default_mapper
        except AttributeError:
            pass
        cls.default_mapper = cls()
        return cls.default_mapper

    def __init__(self, prototype=None):
        self.value_mappers = {}
        self.instance_mappers = {}
        self.__prototype = prototype

    def prototype(self):
      if self.__prototype: 
        return self.__prototype
      if self is self.default():
        return None
      return self.default()
    
    def define_specification_for(self, value, specification):
        self.value_mappers[value] = specification

    def define_specification_for_instances(self, cls, specification_builder):
        self.instance_mappers[cls] = specification_builder

    def new_child_mapper(self):
      return self.__class__(prototype = self)

    def specification_for(self, descriptor):
        specification = self.__find_specification_for(descriptor)
        if specification:
            return specification(self, descriptor)
        else:
            return self.missing_specification(descriptor)

    def __find_specification_for(self, descriptor):
        if safe_in(descriptor, self.value_mappers):
            return self.value_mappers[descriptor]
        elif hasattr(descriptor, '__class__') and descriptor.__class__ in self.instance_mappers:
            return self.instance_mappers[descriptor.__class__]
        elif self.prototype():
            return self.prototype().__find_specification_for(descriptor)
        else:
            return None

    def missing_specification(self, descriptor):
        raise MissingSpecification(descriptor)

def safe_in(x, ys):
    """
    Test if x is present in ys even if x is unhashable.
    """
    try:
        return x in ys
    except TypeError:
        return False


class MissingSpecification(Exception):
    def __init__(self, descriptor):
        Exception.__init__(self, "Unable to produce specification for descriptor %s" % str(descriptor))
