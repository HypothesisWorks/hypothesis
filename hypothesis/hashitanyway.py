def hash_everything(l):
    try:
        return hash(l)
    except TypeError:
        try:
            xs = iter(l)
        except TypeError:
            return 0

        h = 0
        for x in xs:
            h = h ^ hash_everything(x)
        return h

class HashItAnyway(object):
    def __init__(self, wrapped):
        self.wrapped = wrapped
        self.h = hash_everything(wrapped)

    def __eq__(self, other): 
        return (isinstance(other,HashItAnyway) and
                self.wrapped.__class__ == other.wrapped.__class__ and
                self.wrapped == other.wrapped)

    def __ne__(self,other):
        return not(self == other)


    def __hash__(self):
        return self.h

    def __repr__(self):
        return "HashItAnyway(%s)" % repr(self.wrapped)
