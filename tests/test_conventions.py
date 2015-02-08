from hypothesis.conventions import UniqueIdentifier


def test_unique_identifier_repr():
    assert repr(UniqueIdentifier("hello_world")) == "hello_world"
