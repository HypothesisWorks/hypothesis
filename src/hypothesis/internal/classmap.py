class ClassMap(object):
    def __init__(self):
        self.data = {}

    def __getitem__(self, key):
        try:
            return self.data[key]
        except KeyError:
            for c in key.mro():
                try:
                    return self.data[c]
                except KeyError:
                    pass
        raise KeyError(key)

    def __setitem__(self, key, value):
        self.data[key] = value
