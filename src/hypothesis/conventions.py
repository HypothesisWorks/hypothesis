class UniqueIdentifier(object):
    def __init__(self, identifier):
        self.identifier = identifier

    def __repr__(self):
        return self.identifier


not_set = UniqueIdentifier("not_set")
