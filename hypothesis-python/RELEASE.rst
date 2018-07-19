RELEASE_TYPE: patch

This release improves the shrinker's ability to handle situations where there
is an additive constraint between two values.

For example, consider the following test:


.. code-block:: python

    import hypothesis.strategies as st
    from hypothesis import given

    @given(st.integers(), st.integers())
    def test_does_not_exceed_100(m, n):
        assert m + n < 100

Previously this could have failed with almost any pair ``(m, n)`` with
``0 <= m <= n`` and ``m + n == 100``. Now it should almost always fail with
``m=0, n=100``.

This is a relatively niche specialisation, but can be useful in situations
where e.g. a bug is triggered by an integer overflow.
