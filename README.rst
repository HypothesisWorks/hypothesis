==========
Hypothesis
==========

Hypothesis is family of testing libraries which let you write tests parametrized
by a source of examples. A Hypothesis implementation then generates simple an
comprehensible examples that make your tests fail.
This simplifies writing your tests and makes them more powerful at the same time,
by letting software automate the boring bits and do them to a higher standard than a human would,
freeing you to focus on the higher level test logic.

This sort of testing is typically called "property-based testing",
and the most widely known implementation of the concept is the Haskell library `QuickCheck <https://hackage.haskell.org/package/QuickCheck>`_,
but Hypothesis differs significantly from QuickCheck and is designed to fit idiomatically and easily into existing styles of testing that you are useful,
with absolutely no familiarity with Haskell or functional programming needed. 

The currently available implementations of Hypothesis are:

* `Hypothesis for Python <hypothesis-python>`_ is the original implementation,
  and the only one that is currently fully production ready.
* `Hypothesis for Ruby <https://github.com/HypothesisWorks/hypothesis-ruby>`_
  is an ongoing project that we intend to eventually reach parity with
  Hypothesis for Python.
* `Hypothesis for Java <https://github.com/HypothesisWorks/hypothesis-java>`_
  is a prototype written some time ago. It's far from feature complete and is
  not under active development, but was intended to prove the viability of the
  concept.

This repository will eventually house all implementations of Hypothesis, but
we are currently in the process of consolidating the existing repositories into a single one.
