from hypothesis.internal.utils.hashitanyway import HashItAnyway


class Tracker(object):

    def __init__(self):
        self.contents = {}

    def track(self, x):
        k = HashItAnyway(x)
        n = self.contents.get(k, 0) + 1
        self.contents[k] = n
        return n
