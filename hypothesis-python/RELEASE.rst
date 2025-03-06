RELEASE_TYPE: patch

We now provide a better string representation for :func:`~hypothesis.strategies.one_of` strategies, by flattening consecutive ``|`` combinations. For instance:

.. code-block:: pycon

    >>> st.integers() | st.text() | st.booleans()
    # previously: one_of(one_of(integers(), text()), booleans())
    one_of(integers(), text(), booleans())

Explicit calls to :func:`~hypothesis.strategies.one_of` remain unflattened, in order to make tracking down complicated :func:`~hypothesis.strategies.one_of` constructions easier:

.. code-block:: pycon

    >>> st.one_of(st.integers(), st.one_of(st.text(), st.booleans()))
    one_of(integers(), one_of(text(), booleans()))

We print ``one_of`` in reprs (rather than ``integers() | text() | ...``) for consistency with reprs containing ``.filter`` or ``.map`` calls, which uses the full ``one_of`` to avoid ambiguity.
