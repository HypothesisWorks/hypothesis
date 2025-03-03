RELEASE_TYPE: patch

We now provide a better string representation for :func:`~hypothesis.strategies.one_of` strategies, by flattening nested :func:`~hypothesis.strategies.one_of` instances. For instance:

.. code-block:: pycon

    >>> st.integers() | st.text() | st.booleans()
    # previously: one_of(one_of(integers(), text()), booleans())
    one_of(integers(), text(), booleans())
