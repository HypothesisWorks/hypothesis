import pytest

from hypothesis import given, strategy


@pytest.mark.parametrize(("specifier", "condition"), [
    (int, lambda x: x > 1),
    ([int], lambda x: sum(x) > 0),
    ([int], bool),
])
def test_filter_correctly(specifier, condition):
    @given(strategy(specifier).filter(condition))
    def test_is_filtered(x):
        assert condition(x)

    test_is_filtered()
