RELEASE_TYPE: patch

Improve the clarity of printing counterexamples in :doc:`stateful testing <stateful>`, by avoiding confusing :class:`~hypothesis.stateful.Bundle` references with equivalent values drawn from a regular strategy.

For example, we now print:

.. code-block: python

  a_0 = state.add_to_bundle(a=0)
  state.unrelated(value=0)

instead of

.. code-block: python

  a_0 = state.add_to_bundle(a=0)
  state.unrelated(value=a_0)

if the ``unrelated`` rule draws from a regular strategy such as :func:`~hypothesis.strategies.integers` instead of the ``a`` bundle.
