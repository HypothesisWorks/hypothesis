from hypothesis import given


class HasSetupAndTeardown(object):
    def __init__(self):
        self.setups = 0
        self.teardowns = []

    def __repr__(self):
        return "HasSetupAndTeardown()"

    def setup_example(self):
        self.setups += 1

    def teardown_example(self, example):
        self.teardowns.append(example)

    def __copy__(self):
        return self

    def __deepcopy__(self, mapping):
        return self

    @given(int)
    def give_me_an_int(self, x):
        pass

    @given(str)
    def give_me_a_string(myself, x):
        pass


def test_calls_setup_and_teardown_on_self_as_first_argument():
    x = HasSetupAndTeardown()
    x.give_me_an_int()
    x.give_me_a_string()
    assert x.setups > 0
    assert len(x.teardowns) == x.setups
    assert any(isinstance(t[0][1]['x'], int) for t in x.teardowns)
    assert any(isinstance(t[0][1]['x'], str) for t in x.teardowns)


def test_calls_setup_and_teardown_on_self_unbound():
    x = HasSetupAndTeardown()
    HasSetupAndTeardown.give_me_an_int(x)
    assert x.setups > 0
    assert len(x.teardowns) == x.setups
