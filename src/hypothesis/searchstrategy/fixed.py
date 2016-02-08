from __future__ import division, print_function, absolute_import

from hypothesis.control import assume
from hypothesis.searchstrategy.strategies import SearchStrategy


class FixedStrategy(SearchStrategy):

    def __init__(self, block_size):
        self.block_size = block_size

    def do_draw(self, data):
        block = data.draw_bytes(self.block_size, self.distribution)
        assert len(block) == self.block_size
        value = self.from_bytes(block)
        assume(self.is_acceptable(value))
        return value

    def distribution(self, random, n):
        assert n == self.block_size
        for _ in range(100):
            value = self.draw_value(random)
            if self.is_acceptable(value):
                block = self.to_bytes(value)
                assert len(block) == self.block_size
                return block
        raise AssertionError(
            'After 100 tries was unable to draw a valid value. This is a bug '
            'in the implementation of %s.' % (type(self).__name__,))

    def draw_value(self, random):
        raise NotImplementedError('%s.draw' % (
            type(self).__name__,
        ))

    def to_bytes(self, value):
        raise NotImplementedError('%s.to_bytes' % (
            type(self).__name__,
        ))

    def from_bytes(self, value):
        raise NotImplementedError('%s.from_bytes' % (
            type(self).__name__,
        ))

    def is_acceptable(self, value):
        return True
