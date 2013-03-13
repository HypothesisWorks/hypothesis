from hypothesis.tracker import Tracker

def test_track_ints():
    t = Tracker()
    assert not t.already_seen(1)
    assert t.already_seen(1)

def test_track_lists():
    t = Tracker()
    assert not t.already_seen([1])
    assert t.already_seen([1])

def test_nested_unhashables():
    t = Tracker()
    x = {"foo" : [1,2,{3,4,5,6}], "bar" : 10}
    assert not t.already_seen(x)
    assert t.already_seen(x)
    

