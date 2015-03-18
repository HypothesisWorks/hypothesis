from hypothesis.utils.idkey import IdKey


class Friendly(object):
    def __eq__(self, other):
        return True

    def __ne__(self, other):
        return False


def test_id_key_respects_identity():
    x = Friendly()
    y = Friendly()
    assert x == y
    assert not (x != y)

    assert IdKey(x) != x
    assert IdKey(x) == IdKey(x)
    t = IdKey(x)
    assert t == t

    assert IdKey(x) != IdKey(y)
