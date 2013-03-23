from functools import wraps

class SpecificationMapper(object):
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
        self.value_mappers.setdefault(value,[]).append(specification)

    def define_specification_for_instances(self, cls, specification):
        self.instance_mappers.setdefault(cls,[]).append(specification)

    def define_specification_for_classes(self, specification,subclasses_of=None):
        if subclasses_of:
            original_specification = specification
            @wraps(specification)
            def restricted(sms, descriptor):
                if issubclass(descriptor,subclasses_of):
                    return original_specification(sms,descriptor)
                else:
                    return next_in_chain()
            specification = restricted

        self.define_specification_for_instances(typekey(SpecificationMapper), specification)

    def new_child_mapper(self):
      return self.__class__(prototype = self)

    def specification_for(self, descriptor):
        for h in self.__find_specification_handlers_for(descriptor):
            try:
                return h(self, descriptor)
            except NextInChain:
                pass
        return self.missing_specification(descriptor)

    def __find_specification_handlers_for(self, descriptor):
        if safe_in(descriptor, self.value_mappers):
            for h in reversed(self.value_mappers[descriptor]):
                yield h 
        tk = typekey(descriptor)
        if tk in self.instance_mappers:
            for h in reversed(self.instance_mappers[tk]):
                yield h
        if self.prototype():
            for h in self.prototype().__find_specification_handlers_for(descriptor):
                yield h

    def missing_specification(self, descriptor):
        raise MissingSpecification(descriptor)

def typekey(x):
    try:
        return x.__class__
    except AttributeError:
        return type(x)

def safe_in(x, ys):
    """
    Test if x is present in ys even if x is unhashable.
    """
    try:
        return x in ys
    except TypeError:
        return False

def next_in_chain():
    raise NextInChain()

class NextInChain(Exception):
    def __init__(self):
        Exception.__init__(self, "Not handled. Call next in chain. You shouldn't have seen this exception.")

class MissingSpecification(Exception):
    def __init__(self, descriptor):
        Exception.__init__(self, "Unable to produce specification for descriptor %s" % str(descriptor))
