Targeted property-based testing
===============================

Targeted property-based testing combines the advantages of both search-based and property-based testing.  Instead of being completely random, targeted PBT uses a search-based component to guide the input generation towards values that have a higher probability of falsifying a property.  This explores the input space more effectively and requires fewer tests to find a bug or achieve a high confidence in the system being tested than random PBT. (`Löscher and Sagonas <http://proper.softlab.ntua.gr/Publications.html>`__)

This is not *always* a good idea - for example calculating the search metric might take time better spent running more uniformly-random test cases, or your target metric might accidentally lead Hypothesis *away* from bugs - but if there is a natural metric like "floating-point error", "load factor" or "queue length", we encourage you to experiment with targeted testing.

.. code-block:: python

  from hypothesis import given, strategies as st, target


  @given(st.floats(0, 1e100), st.floats(0, 1e100), st.floats(0, 1e100))
  def test_associativity_with_target(a, b, c):
      ab_c = (a + b) + c
      a_bc = a + (b + c)
      difference = abs(ab_c - a_bc)
      target(difference)  # Without this, the test almost always passes
      assert difference < 2.0

.. autofunction:: hypothesis.target

We recommend that users also skim the papers introducing targeted PBT; from `ISSTA 2017 <http://proper.softlab.ntua.gr/papers/issta2017.pdf>`__ and `ICST 2018 <http://proper.softlab.ntua.gr/papers/icst2018.pdf>`__. For the curious, the initial implementation in Hypothesis uses hill-climbing search via a mutating fuzzer, with some tactics inspired by simulated annealing to avoid getting stuck and endlessly mutating a local maximum.
