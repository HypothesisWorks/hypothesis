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
        return isinstance(other,HashItAnyway) and self.wrapped == other.wrapped

    def __hash__(self):
        return self.h


class Tracker(object):
    def __init__(self):
        self.contents = {}

    def track(self,x):
        k = HashItAnyway(x)
        n = self.contents.get(k, 0) + 1 
        self.contents[k] = n
        return n

    def __iter__(self):
        for k,v in self.contents.items():
            yield k.wrapped, v
