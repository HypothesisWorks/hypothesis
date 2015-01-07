import hypothesis.searchstrategy as ss
from hypothesis.flags import Flags


def flags(*args, **kwargs):
    return ss.SearchStrategies().strategy(*args, **kwargs).flags().flags


def test_tuple_contains_all_child_flags():
    assert flags(int).issubset(flags((int, str)))
    assert flags(str).issubset(flags((int, str)))


def test_one_of_contains_all_child_flags():
    assert flags(int).issubset(flags(ss.one_of([int, str])))
    assert flags(str).issubset(flags(ss.one_of([int, str])))


def test_list_contains_all_child_flags():
    assert flags(int).issubset(flags([int]))
    assert flags(int).issubset(flags([int, str]))
    assert flags(str).issubset(flags([int, str]))


def test_flags_not_enabled_by_default():
    flags = Flags()
    assert not flags.enabled('foo')


def test_enabling_flags_leaves_original_unchanged():
    flags = Flags()
    assert not flags.enabled('foo')
    flags2 = flags.with_enabled('foo')
    assert not flags.enabled('foo')
    assert flags2.enabled('foo')


def test_can_disable_flags():
    flags = Flags(['foo'])
    assert flags.enabled('foo')
    flags2 = flags.with_disabled('foo')
    assert not flags2.enabled('foo')


def test_str_contains_flags():
    assert 'foo' in str(Flags(['foo']))
    assert 'foo' in str(Flags(['foo', 'bar']))
    assert 'bar' in str(Flags(['foo', 'bar']))
