from hypothesis import given, strategy, assume, Settings
from hypothesis.specifiers import just, integers_in_range


ConstantLists = strategy(int).flatmap(lambda i: [just(i)])

OrderedPairs = strategy(integers_in_range(1, 200)).map(
    lambda e: integers_in_range(0, e - 1)
)

with Settings(max_examples=200):
    @given(ConstantLists)
    def test_constant_lists_are_constant(x):
        assume(len(x) >= 3)
        assert len(set(x)) == 1

    @given(OrderedPairs)
    def test_in_order(x):
        assert x[0] < x[1]
