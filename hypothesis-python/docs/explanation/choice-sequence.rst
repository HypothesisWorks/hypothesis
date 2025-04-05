The choice sequence
===================

.. note::

    This page is about Hypothesis internals. You aren't expected to understand this in order to use Hypothesis. In fact, we go to great lengths to ensure you don't have to! If you *want* the details, this page is for you.

The **choice sequence** is how Hypothesis represents examples internally. It is the foundational definition in Hypothesis, and underlies generation, :doc:`shrinking <shrinking>`, and mutation.

The best way to understand the choice sequence is to examine how Hypothesis generates inputs. Consider the following test, which takes lists of numbers:

.. code-block:: python

    from hypothesis import strategies as st


    @given(st.lists(st.integers() | st.floats()))
    def test_list(l):
        print(f"called with {l}")

Concretely, how should Hypothesis generate random examples for ``test_list``? We could hardcode some distribution specifically for lists of (integers or floats). But this wouldn't compose well or generalize to other element strategies.

Instead, Hypothesis treats every strategy as making a series of random choices. Hypothesis then builds up an input by asking each component strategy to make those choices in turn. Internally, for our strategy above:

- |st.lists| first chooses a random boolean to decide whether to add a new list element.
- If so, |st.one_of| (represented by the pipe ``|``) chooses a random integer between 0 and 1 to decide which component strategy to use.
- If ``0``, we use |st.integers|, which chooses a random integer.
- If ``1``, we use |st.floats|, which chooses a random float.
- Afterwards, we continue from the top, checking |st.lists| to see if we should add another element.

For instance, the series of random choices ``[True, 0, 1, True, 1, 3.5, False]`` corresponds to the list ``[0, 3.5]`` [#grammar]_. If Hypothesis had made this series of random choices, we would have seen ``called with [0, 3.5]`` as output. Notice that despite generating the list ``[0, 3.5]``, Hypothesis represented that list internally using only a series of booleans, integers, and floats—with no list in sight.

In Hypothesis, inputs for *any* strategy, no matter how complicated, are represented internally as a sequence of one of a small number of primitives. We call this the *choice sequence*, because each primitive represents a random choice.

The current primitives of the choice sequence are |int|, |bool|, |float|, |str|, and |bytes|.

In addition to the choice sequence, Hypothesis also tracks spans of related choices. For instance, the boolean choice in |st.lists| to decide to add a new element, and the following choices to actually add that element, are marked as belonging to the same span. Tracking spans turns the choice sequence from a flat list into a tree structure. This tree view of the choice sequence — as well as spans in general — are used to give more information about the test case structure to shrinking and mutation during generation.

.. [#grammar] For those familiar with grammars, each strategy corresponds to a grammar, and generation corresponds to following production rules of this grammar. In general, strategies form a context free grammar. The exceptions are |st.data| and |st.composite|. When those strategies are used, the grammar could be fully recursively enumerable, because the parsing behavior is determined by arbitrary python code.
