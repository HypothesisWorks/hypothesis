from tests.common import timeout
from hypothesis import given, strategy, assume
from hypothesis.core import _debugging_return_failing_example
from hypothesis.internal.compat import text_type, binary_type
import pytest


@pytest.mark.parametrize(('string',), [(text_type,), (binary_type,)])
def test_minimal_unsorted_strings(string):
    def dedupe(xs):
        result = []
        for x in xs:
            if x not in result:
                result.append(x)
        return result

    @timeout(5)
    @given(strategy([string]).map(dedupe))
    def is_sorted(xs):
        assume(len(xs) >= 10)
        print(xs)
        assert sorted(xs) == xs

    with _debugging_return_failing_example.with_value(True):
        result = is_sorted()[1]['xs']
        assert len(result) == 10
        assert all(len(r) <= 2 for r in result)
