import pytest

from hypothesis.errors import InvalidArgument
from hypothesis.searchstrategy.numbers import WideRangeIntStrategy
from hypothesis.searchstrategy.strategies import OneOfStrategy, SearchStrategy
from hypothesis.stateful import validate_rule_arguments


def test_invalid_rule_arguments():
    # Each invalid argument is expected to raise an InvalidArgument error.
    invalid_arguments = [
        {"invalid_arg1": "Not a strategy"},
        {"strategy": object()},
        {"strategy": [SearchStrategy()]},
    ]
    for invalid_kwargs in invalid_arguments:
        with pytest.raises(InvalidArgument):
            validate_rule_arguments(kwargs=invalid_kwargs)


def test_valid_rule_arguments():
    msg = "Valid kwargs values are expected to be a strategy instance," \
          " %s was received instead and raised an error "
    # All valid arguments are expected to pass validation without error.
    valid_arguments = [
        {"strategy": SearchStrategy()},
        {"strategy": OneOfStrategy(strategies=(SearchStrategy(),))},
        {"strategy": WideRangeIntStrategy()},
    ]
    for valid_kwargs in valid_arguments:
        try:
            assert validate_rule_arguments(kwargs=valid_kwargs) is None
        except InvalidArgument:
            raise AssertionError(msg % (valid_kwargs,))
