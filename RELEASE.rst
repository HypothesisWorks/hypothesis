RELEASE_TYPE: minor

This release adds a ``unique`` argument to :func:`~hypothesis.extra.numpy.arrays`
which behaves the same ways as the corresponding one for
:func:`~hypothesis.strategies.lists`, requiring all of the elements in the
generated array to be distinct.
