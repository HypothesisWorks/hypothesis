RELEASE_TYPE: patch

The ``.seed()`` method of :func:`~hypothesis.strategies.randoms` now accepts
the same arguments as :meth:`random.Random.seed`, such as ``a=`` and
``version=``. Previously, it required exactly one positional argument.
Calling ``.seed()`` without a seed now raises a clearer error.
