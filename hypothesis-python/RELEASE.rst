RELEASE_TYPE: patch

This release fixes a bug related to the falsifying examples produced by
stateful testing with multiple results. The ``MultipleResults`` is now
iterable, which allows for proper unpacking.
