from random import Random


class RandomWithSeed(Random):

    """A subclass of Random designed to expose the seed it was initially
    provided with.

    We consistently use this instead of Random objects because it makes
    examples much easier to recreate.

    """

    def __init__(self, seed):
        super(RandomWithSeed, self).__init__(seed)
        self.seed = seed

    def __repr__(self):
        return 'RandomWithSeed(%s)' % (self.seed,)

    def __copy__(self):
        r = RandomWithSeed(self.seed)
        r.setstate(self.getstate())
        return r

    def __hash__(self):
        return hash(self.seed)

    def __deepcopy__(self, d):
        return self.__copy__()

    def __eq__(self, other):
        return self is other or (
            isinstance(other, RandomWithSeed) and
            self.seed == other.seed
        )

    def __ne__(self, other):
        return not self.__eq__(other)
