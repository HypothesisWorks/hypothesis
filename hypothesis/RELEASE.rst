RELEASE_TYPE: patch

This patch speeds up shrinking of collections such as :func:`~hypothesis.strategies.lists`,
by deleting contiguous runs of elements adaptively.  Removing a run of ``n``
deletable elements now takes ``O(log(n))`` internal test calls rather than
``O(n)``.
