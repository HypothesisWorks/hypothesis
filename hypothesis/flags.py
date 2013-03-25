class Flags(object):
    def __init__(self, flags=None):
        self.flags = frozenset(flags or {})

    def __repr__(self):
        return "Flags(%s)" % ', '.join(map(str,self.flags))

    def __hash__(self):
        return hash(self.flags)

    def __eq__(self, other):
        return isinstance(other, Flags) and self.flags == other.flags

    def __ne__(self, other):
        return not (self == other)

    def enabled(self, flag):
        return flag in self.flags

    def with_enabled(self, *flags):
        x = set(self.flags)
        for f in flags:
            x.add(f)
        return Flags(x)

    def with_disabled(self, *flags):
        x = set(self.flags)
        for f in flags:
            x.remove(f)
        return Flags(x)
