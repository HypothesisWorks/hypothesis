from hypothesis.hashitanyway import HashItAnyway

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
