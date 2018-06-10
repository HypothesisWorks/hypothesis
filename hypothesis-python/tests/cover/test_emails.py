from hypothesis import given
from hypothesis.strategies import emails


@given(emails())
def test_is_valid_email(address):
    local, at_, domain = address.rpartition('@')
    assert at_ == '@'
    assert local
    assert domain
