from functools import wraps
from hypothesis.internal.utils.hashitanyway import HashItAnyway


class SpecificationMapper(object):
    """Maps descriptions of some type to a type. Has configurable handlers for
    what a description may look like. Handlers for descriptions may take either
    a specific value or all instances of a type and have access to the mapper
    to look up types.

    Also supports prototype based inheritance, with children being able to
    override specific handlers

    There is a single default() object per subclass of SpecificationMapper
    which everything has as a prototype if it's not assigned any other
    prototype. This allows you to define the mappers on the default object
    and have them inherited by any custom mappers you want.
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
        self.__descriptor_cache = {}

    def prototype(self):
        if self.__prototype:
            return self.__prototype
        if self is self.default():
            return None
        return self.default()

    def define_specification_for(self, value, specification):
        self.value_mappers.setdefault(value, []).append(specification)
        self.__descriptor_cache = {}

    def define_specification_for_instances(self, cls, specification):
        self.instance_mappers.setdefault(cls, []).append(specification)
        self.__descriptor_cache = {}

    def define_specification_for_classes(
            self, specification, subclasses_of=None):
        if subclasses_of:
            original_specification = specification

            @wraps(specification)
            def restricted(sms, descriptor):
                if issubclass(descriptor, subclasses_of):
                    return original_specification(sms, descriptor)
                else:
                    return next_in_chain()
            specification = restricted

        self.define_specification_for_instances(
            typekey(SpecificationMapper),
            specification)

    def new_child_mapper(self):
        return self.__class__(prototype=self)

    def specification_for(self, descriptor):
        k = HashItAnyway(descriptor)
        if k in self.__descriptor_cache:
            return self.__descriptor_cache[k]

        for h in self.find_specification_handlers_for(descriptor):
            try:
                r = h(self, descriptor)
                break
            except NextInChain:
                pass
        else:
            r = self.missing_specification(descriptor)

        self.__descriptor_cache[k] = r
        return r

    def has_specification_for(self, descriptor):
        try:
            self.specification_for(descriptor)
            return True
        except MissingSpecification:
            return False

    def find_specification_handlers_for(self, descriptor):
        if safe_in(descriptor, self.value_mappers):
            for h in reversed(self.value_mappers[descriptor]):
                yield h
        tk = typekey(descriptor)
        for h in self.__instance_handlers(tk):
            yield h
        if self.prototype():
            for h in self.prototype().find_specification_handlers_for(
                    descriptor):
                yield h

    def __instance_handlers(self, tk):
        for c, hs in sort_in_subclass_order(
                self.instance_mappers.items(),
                lambda x: x[0],
        ):
            if issubclass(tk, c):
                for h in reversed(hs):
                    yield h

    def missing_specification(self, descriptor):
        raise MissingSpecification(descriptor)


def sort_in_subclass_order(xs, get_class=lambda x: x):
    if len(xs) <= 1:
        return list(xs)
    by_class = {}
    for x in xs:
        c = get_class(x)
        by_class.setdefault(c, []).append(x)
    classes = list(by_class.keys())
    subclasses = {}
    for c in classes:
        children = subclasses.setdefault(c, [])
        for d in classes:
            if c != d and issubclass(d, c):
                children.append(d)
    in_order = []

    def recurse(c):
        if c in in_order:
            return
        for d in subclasses[c]:
            recurse(d)
        in_order.append(c)

    while classes:
        recurse(classes.pop())
    return [
        x
        for c in in_order
        for x in by_class[c]
    ]


def typekey(x):
    return x.__class__


def safe_in(x, ys):
    """Test if x is present in ys even if x is unhashable."""
    try:
        return x in ys
    except TypeError:
        return False


def next_in_chain():
    raise NextInChain()


class NextInChain(Exception):
    def __init__(self):
        Exception.__init__(
            self,
            "Not handled. Call next in chain. You shouldn't have seen this"
            "exception.")


class MissingSpecification(Exception):

    def __init__(self, descriptor):
        Exception.__init__(
            self,
            'Unable to produce specification for descriptor %s' %
            str(descriptor))
