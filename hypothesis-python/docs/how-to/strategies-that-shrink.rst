How to write strategies that shrink well
========================================

.. TODO_DOCS

.. .. note::

..     It may also be helpful to read the :doc:`shrinking explanation </explanation/shrinking>` page (but we will not assume knowledge of it in this how-to guide).

The Hypothesis shrinker is world-class, but is *not* magic. Some ways of writing strategies will shrink better than others. By "shrinks better" and "shrinks well", we mean both that Hypothesis spends less time shrinking, and that it finds simpler failing example more often.

Keep the following tips in mind for writing strategies that shrink well:

* If a value depends on another value, generate them near each other.
* Place simpler strategies first in |st.one_of|.
* Structure generation so that deleting (one or more) consecutive choices shrinks the example.

Read on for more detail about each of these.

Generate related values near each other
---------------------------------------

If two generated values interact in your code, try to generate them near each other. The reason is that the shrinker assumes that nearby choices are more likely to be related, and limits some shrinking passes to reducing only choices made near each other.

For example:

.. code-block:: python

    # bad
    @given(
        st.integers(),
        st.booleans(),
        st.binary(),
        st.text(),
    )
    def f(n, v1, v2, s):
        assert n != len(s)


    # good
    @given(
        st.integers(),
        st.text(),  # <-- changed
        st.booleans(),
        st.binary(),
    )
    def f(n, s, v1, v2):
        assert n != len(s)

This also applies to |@composite| and |st.data|:

.. code-block:: python

    # bad
    @st.composite
    def values(draw):
        n = draw(st.integers())
        v1 = draw(st.booleans())
        v2 = draw(st.binary())
        s = draw(st.text())
        return (n, s)


    @given(values())
    def f(v):
        (n, s) = v
        assert n != len(s)


    # good
    @st.composite
    def values(draw):
        n = draw(st.integers())
        s = draw(st.text())  # <-- changed
        v1 = draw(st.booleans())
        v2 = draw(st.binary())
        return (n, s)


    @given(values())
    def f(value):
        (n, s) = value
        assert n != len(s)


Place simpler strategies first in |st.one_of|
---------------------------------------------

When combining strategies with |st.one_of| or ``|``, place simpler strategies earlier (more to the left). The shrinker shrinks to earlier strategies in |st.one_of|, so if you place a simple strategy in the first position instead of a more complicated one, you may help the shrinker avoid a lot of unnecessary work in shrinking the more complicated strategy.


Structure generation so that deleting choices shrinks
-----------------------------------------------------

Here's one strategy you might be tempted to write:

.. code-block:: python

    @st.composite
    def values(draw):
        n = draw(st.integers())
        l = draw(st.lists(st.integers(min_size=n)))

In order to remove a list element from this strategy, the shrinker has to both reduce ``n`` by one while simultaneously removing the list element. This can be hard for the shrinker, because the choice for ``n`` might be made far away from later list elements. Strategies of this form are therefore unlikely to shrink well.

.. note::

    This particular strategy actually *does* shrink well in Hypothesis, but only because this is such a common way to shrink poorly that the shrinker contains special logic for the common case. It's not hard for slightly more complex strategies to trip up the shrinker for the same underlying reason, though.

What will shrink better is allowing each element to be deleted without requiring a separate choice like ``n`` to be changed.

We can do this by getting rid of ``n`` entirely, and instead draw a boolean every time we want to add an element:

.. code-block:: python

    @st.composite
    def values(draw):
        l = []
        while draw(st.booleans()):
            l.append(st.integers())

The sequences of choices now looks something like ``[True, 0, True, 12, True, -3, False]`` for the list ``[0, 12, -3]``. This lets the shrinker remove an element by deleting two consecutive choices like ``[True, -3]``, which is much easier than needing to simultaneously lower a separate ``n`` choice. This strategy will shrink very well.

Fun fact: this is how Hypothesis implements |st.lists| generation internally, for the exact reason that it shrinks better than choosing a pre-determined size!
