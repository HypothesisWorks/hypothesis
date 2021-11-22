RELEASE_TYPE: patch

This patch changes the backing datastructures of :func:`~hypothesis.register_random`
and a few internal caches to use :class:`weakref.WeakKeyDictionary`.  This reduces
memory usage and may improve performance when registered :class:`~random.Random`
instances are only used for a subset of your tests (:issue:`3131`).
