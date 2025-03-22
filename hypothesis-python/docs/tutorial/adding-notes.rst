Adding notes
============

Normally the output of a failing test will look something like:

.. code::

    Falsifying example: test_a_thing(x=1, y="foo")

With the ``repr`` of each keyword argument being printed.

Sometimes this isn't enough, either because you have a value with a ``__repr__()`` method that isn't very descriptive or because you need to see the output of some intermediate steps of your test. That's where |note| comes in:

.. code-block:: pycon

    >>> from hypothesis import given, note, strategies as st
    >>> @given(st.lists(st.integers()), st.randoms())
    ... def test_shuffle_is_noop(ls, r):
    ...     ls2 = list(ls)
    ...     r.shuffle(ls2)
    ...     note(f"Shuffle: {ls2!r}")
    ...     assert ls == ls2
    ...
    >>> try:
    ...     test_shuffle_is_noop()
    ... except AssertionError:
    ...     print("ls != ls2")
    ...
    Falsifying example: test_shuffle_is_noop(ls=[0, 1], r=RandomWithSeed(1))
    Shuffle: [1, 0]
    ls != ls2

The note is printed for the minimal failing example of the test in order to include any additional information you might need in your test.
