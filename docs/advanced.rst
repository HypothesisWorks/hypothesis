=================
Advanced features
=================

~~~~~~~~~~~~~~~~~~
Making assumptions
~~~~~~~~~~~~~~~~~~

Sometimes a SearchStrategy doesn't produce exactly the right sort of data you want.

For example suppose had the following test:


.. code:: python

  from hypothesis import given

  @given(float)
  def test_negation_is_self_inverse(x):
      assert x == -(-x)
      

Running this gives us:

.. 

  Falsifying example: test_negation_is_self_inverse(x=float('nan'))
  AssertionError

This is annoying. We know about NaN and don't really care about it, but as soon as Hypothesis
finds a NaN example it will get distracted by that and tell us about it. Also the test will
fail and we want it to pass.

So lets block off this particular example:

.. code:: python

  from hypothesis import given, assume
  from math import isnan

  @given(float)
  def test_negation_is_self_inverse_for_non_nan(x):
      assume(not isnan(x))
      assert x == -(-x)

And this passes without a problem.

assume throws an exception which terminates the test when provided with a false argument.
It's essentially an assert, except that the exception it throws is one that Hypothesis
identifies as meaning that this is a bad example, not a failing test.

In order to avoid the easy trap where you assume a lot more than you intended, Hypothesis
will fail a test when it can't find enough examples passing the assumption.

If we'd written:

.. code:: python

  from hypothesis import given, assume

  @given(float)
  def test_negation_is_self_inverse_for_non_nan(x):
      assume(False)
      assert x == -(-x)


Then on running we'd have got the exception:

.. 

  Unsatisfiable: Unable to satisfy assumptions of hypothesis test_negation_is_self_inverse_for_non_nan. Only 0 examples found after 0.0791318 seconds
  

