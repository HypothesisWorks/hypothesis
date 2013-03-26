from hypothesis.descriptorkey import DescriptorKey as dk

def test_dk_ints_are_equal():
    assert dk(1) == dk(1)
    assert dk(1) != dk(2)

def test_recursive_lists_are_equal():
    x = []
    x.append(x)
    y = []
    y.append(y)

    assert dk(x) == dk(y)

def test_mutually_recursive_lists_are_equal():
    x = []
    y = []
    x.append(y)
    y.append(x)
    assert dk(x) == dk(y)

def test_mutually_recursive_lists_are_equal_to_self_recursive_lists():
    x = []
    y = []
    x.append(y)
    y.append(x)
    z = []
    z.append(z)
    assert dk(x) == dk(z)
