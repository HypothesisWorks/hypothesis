""""external" methods.

They're still single dispatch but are not defined on the class.

"""

from hypothesis.internal.classmap import ClassMap


class ExtMethod(object):

    def __init__(self):
        self.mapping = ClassMap()

    def extend(self, typ):
        def accept(f):
            self.mapping[typ] = f
            return f

        return accept

    def __call__(self, typekey, *args, **kwargs):
        try:
            f = self.mapping[typekey]
        except KeyError:
            raise NotImplementedError(
                'No implementation available for %s' % (typekey.__name__,)
            )
        return f(*args, **kwargs)
