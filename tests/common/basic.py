from __future__ import division, print_function, absolute_import, \
    unicode_literals

from hypothesis.searchstrategy import BasicStrategy
from hypothesis.internal.compat import hrange


def simplify_bitfield(random, value):
    for i in hrange(128):
        k = 1 << i
        if value & k:
            yield value & (~k)


class BoringBitfields(BasicStrategy):

    def generate(self, random, parameter_value):
        return random.getrandbits(128)


class Bitfields(BasicStrategy):

    def generate_parameter(self, random):
        return random.getrandbits(128)

    def generate(self, random, parameter_value):
        return parameter_value & random.getrandbits(128)

    def simplify(self, random, value):
        return simplify_bitfield(random, value)

    def copy(self, value):
        return value
