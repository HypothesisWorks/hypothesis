RELEASE_TYPE: patch

This release improves the shrinker's ability to reorder examples.

For example, consider the following test:

.. code-block:: python

    import hypothesis.strategies as st
    from hypothesis import given

    @given(st.text(), st.text())
    def test_non_equal(x, y):
        assert x != y

Previously this could have failed with either of ``x="", y="0"`` or
``x="0", y=""``. Now it should always fail with ``x="", y="0"``.

This will allow the shrinker to produce more consistent results, especially in
cases where test cases contain some ordered collection whose actual order does
not matter.
