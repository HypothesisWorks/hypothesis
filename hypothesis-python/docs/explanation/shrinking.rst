Shrinking
=========

.. note::

    You may also be interested in David MacIver's 2020 paper about the Hypothesis shrinker\: `Test-Case Reduction via Test-Case Generation: Insights from the Hypothesis Reducer <https://www.doc.ic.ac.uk/~afd/papers/2020/ECOOP_Hypothesis.pdf>`_. Note however that Hypothesis has since moved from the bytestring discussed in that paper to the :doc:`choice sequence <choice-sequence>`, including in the shrinker.

The shrinker is the part of Hypothesis which takes a failing example and reduces it into a simpler one before reporting it to you. This makes the failures that you get from your tests easier to debug.

The shrinker in Hypothesis contains a number of heuristics, and is continuously evolving. We sketch the overall design here, but do not give the full algorithm. For that, see the `shrinker source code <https://github.com/HypothesisWorks/hypothesis/blob/master/hypothesis-python/src/hypothesis/internal/conjecture/shrinker.py>`__.


Shrinking passes
----------------

The shrinker defines a number of shrinking passes over the example, each of which makes one particular kind of reduction. While the shrinker has many passes, the core of the shrinker is made up of just the following two passes.

Reducing choices
~~~~~~~~~~~~~~~~

One core shrinking pass attempts to minimize each individual choice in the :doc:`choice sequence <choice-sequence>`. We can see this pass in action here (setting the |settings.report_multiple_bugs| setting to ``False`` so Hypothesis immediately shrinks any failures rather than searching for more, and disabling the |settings.database| setting so you can see different kinds of shrinks by running multiple times):

.. code-block:: python

    from hypothesis import given, settings, strategies as st

    @given(st.integers())
    @settings(report_multiple_bugs=False, database=None)
    def f(n):
        print(n, "<-- failure" if n >= 100 else "")
        assert n < 100

    f()

Here's my output — yours will be different, but follow a similar general pattern:

.. code-block:: none

    0
    -88
    -24
    -32
    31695 <-- failure
    31695 <-- failure
    1
    15311 <-- failure
    7119 <-- failure
    3023 <-- failure
    975 <-- failure
    15
    207 <-- failure
    79
    103 <-- failure
    51
    101 <-- failure
    99
    100 <-- failure
    -1
    36
    50
    98
    -36
    -50
    -98
    -99
    100 <-- failure

Hypothesis finds an initial failure of ``31695``, and then transitions into the shrinking phase. It quickly reduces ``31695`` to ``975``, but goes too far to ``15``. It then backtracks to ``207`` and has a bit of back and forth of binary searching its way down to ``100``. ``100`` is the smallest possible failure, but Hypothesis doesn't know that yet, so it tries a few more reductions before concluding that ``100`` is the best it can do.

Deleting choices
~~~~~~~~~~~~~~~~

Another core shrinking pass tries deleting choices from the choice sequence. Here's a failure which requires removing list elements to reduce, if we generate an initial failing list with a large length:

.. code-block:: python

    from hypothesis import given, settings, strategies as st

    @given(st.lists(st.integers()))
    @settings(report_multiple_bugs=False, database=None)
    def f(lst):
        print(lst, "<-- failure" if len(lst) > 1 else "")
        assert len(lst) <= 1

    f()

Here's my output, where we can see this pass removing list elements which are not relevant to the failure:

.. code-block:: none

    []
    [0]
    [19578, -3592, 4925] <-- failure
    [19578, -3592, 4925] <-- failure
    [19578, -3592, 0] <-- failure
    [19578, -3592] <-- failure
    [19578, 0] <-- failure
    [19578]
    [0, 0] <-- failure
    [0, 0] <-- failure

Hypothesis generates ``[19578, -3592, 4925]`` as the first failure, then transitions into shrinking it. It tries removing elements in succession, then realizes that removing any further elements will not be useful once it hits ``[19578]``, which is not a failure. It then reduces each list element and ends at the minimal failing example of ``[0, 0]``.

Other shrinking passes
----------------------

These two passes (reducing individual choices and removing choices) form the core of the shrinker. However, there are a number of additional shrinking passes in Hypothesis. Most of these reduce failures that have a specific relationship between two or more choices. For instance, one shrinking pass tries to balance two integers so they add up to some target (which the shrinker doesn't know about ahead of time):

.. code-block:: python

    from hypothesis import given, settings, strategies as st

    @given(st.integers(), st.integers())
    @settings(report_multiple_bugs=False, database=None)
    def f(n1, n2):
        print(n1, n2, "<-- failure" if n1 >= 5 and n1 + n2 >= 50 else "")
        if n1 >= 5:
            assert n1 + n2 < 50

    f()

Here's a portion of the output, focusing on when this shrinking pass gets ran:

.. code-block:: none

    ...
    -8 41
    8 42 <-- failure
    7 43 <-- failure
    6 44 <-- failure
    5 45 <-- failure
    4 46
    4 44
    ...

We can see that this pass increases ``n1`` by the same amount that it decreases ``n2`` by. Hypothesis eventually reports that the failure ``n1=5, n2=45``, which is in fact the minimal failing example.

Definition of example complexity
--------------------------------

How does the shrinker know when one example is "simpler" than another? Hypothesis defines a total ordering over the complexity of examples by using the :doc:`choice sequence <choice-sequence>`. Examples are ordered first by the number of choices. If one example makes fewer choices than another, the shrinker will consider it to be simpler, regardless of the type of those choices. If two examples make the same number of choices, the shrinker then orders them by a type-specific notion of complexity for each of the five choice sequence types. For example, the shrinker orders integers as ``0, 1, -1, 2, -2, 3, -3, ...``, with ``0`` being the simplest integer choice.

The shrinker shrinks choices, not examples
------------------------------------------

A common misconception is that the shrinker directly shrinks the value of an example. Instead, the shrinker actually shrinks the underlying :doc:`choice sequence </explanation/choice-sequence>` of the value. For instance, consider the following strategy:

.. code-block:: python

    @given(st.integers(0, 50) | st.just(100))
    def test_n(n):
        assert 0 <= n <= 10

Here, the choice sequence of ``[1]`` (with |st.one_of| choosing to select the second strategy of ``st.just(100)``) corresponds to the value ``100``. It is tempting to think that Hypothesis shrinks the value ``100``, but this is not accurate. Instead, Hypothesis shrinks the underlying choice sequence of ``[1]``.

Because the first branch of |st.one_of| involves two choices (one for |st.one_of| and one for |st.integers|), and the second branch involves only one choice (for |st.one_of|), Hypothesis shrinks to the value ``100``, which involves one fewer choice than the intuitively-simplest ``n=11``.
