==========
Hypothesis
==========

Hypothesis is a family of testing libraries which let you write tests parametrized
by a source of examples. A Hypothesis implementation then generates simple and
comprehensible examples that make your tests fail.
This simplifies writing your tests and makes them more powerful at the same time,
by letting software automate the boring bits and do them to a higher standard than a human would,
freeing you to focus on the higher level test logic.

This sort of testing is often called "property-based testing",
and the most widely known implementation of the concept is the Haskell
library `QuickCheck <https://hackage.haskell.org/package/QuickCheck>`_,
but Hypothesis differs significantly from QuickCheck and is designed to fit
idiomatically and easily into existing styles of testing that you are used to,
with absolutely no familiarity with Haskell or functional programming needed.

`Hypothesis for Python <hypothesis-python>`_ is the original implementation,
and the only one that is currently fully production ready and actively maintained.

------------------------------
Hypothesis for Other Languages
------------------------------

The core ideas of Hypothesis are language agnostic and in principle it is
suitable for any language. We are interested in developing and supporting
implementations for a wide variety of languages, but currently lack the
resources to do so, so our porting efforts are mostly prototypes.

The two prototype implementations of Hypothesis for other languages are:

* `Hypothesis for Ruby <hypothesis-ruby>`_
  is a reasonable start on a port of Hypothesis to Ruby.
* `Hypothesis for Java <https://github.com/HypothesisWorks/hypothesis-java>`_
  is a prototype written some time ago. It's far from feature complete and is
  not under active development, but was intended to prove the viability of the
  concept.

Additionally there is a port of the core engine of Hypothesis, Conjecture, to
Rust. It is not feature complete but in the long run we are hoping to move
much of the existing functionality to Rust and rebuild Hypothesis for Python
on top of it, greatly lowering the porting effort to other languages.

Any or all of these could be turned into full fledged implementations with relatively
little effort (no more than a few months of full time work), but as well as the
initial work this would require someone prepared to provide or fund ongoing
maintenance efforts for them in order to be viable.
