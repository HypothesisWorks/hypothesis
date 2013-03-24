def hash_everything(l,stack=None):
    stack = stack or []
    starting_length = len(stack)
    if any((x is l for x in stack)):
        return 0
    stack.append(l)
    try:
        return hash(l)
    except TypeError:
        h = hash(l.__class__)
        
        try:
            xs = iter(l)
        except TypeError:
            return h

        for x in xs:
            h = h ^ hash_everything(x, stack)
        return h
    finally:
        stack.pop()
        assert starting_length == len(stack)

class HashItAnyway(object):
    def __init__(self, wrapped):
        self.wrapped = wrapped
        self.h = hash_everything(wrapped)

    def __eq__(self, other): 
        return (isinstance(other,HashItAnyway) and
                self.wrapped.__class__ == other.wrapped.__class__ and
                self.h == other.h and
                self.wrapped == other.wrapped)

    def __ne__(self,other):
        return not(self == other)


    def __hash__(self):
        return self.h

    def __repr__(self):
        return "HashItAnyway(%s)" % repr(self.wrapped)
