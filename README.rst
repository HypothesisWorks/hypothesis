==========
Hypothesis
==========

Hypothesis is a family of testing libraries that let you write tests parametrized
by a source of examples. A Hypothesis implementation then generates simple and
comprehensible examples that make your tests fail.
This simplifies writing your tests and makes them more powerful at the same time.
Let software automate the boring bits and do them to a higher standard than a human would,
allowing you to focus on the higher-level test logic.

This sort of testing is often called "property-based testing",
and the most widely known implementation of the concept is the Haskell
library `QuickCheck <https://hackage.haskell.org/package/QuickCheck>`_.
Hypothesis differs significantly from QuickCheck and is designed to fit
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
  is a reasonable start on a port of Hypothesis to Ruby. It worked pretty well
  but uses a core Rust implementation that is unfortunately not compatible with
  recent versions of Rust, due to its dependency on Helix (which now seems to
  be mostly unmaintained).  As a result, Hypothesis for Ruby is currently unsupported pending a
  rewrite of the bridging code between Rust and Ruby. We don't have
  the time or funding for this project at the present time, but it is likely not a massive undertaking
  if anyone would like to provide either of these.
* `Hypothesis for Java <https://github.com/HypothesisWorks/hypothesis-java>`_
  is a prototype written some time ago. It's far from feature complete and is
  not under active development, but was intended to prove the viability of the
  concept.

There is a port of the core engine of Hypothesis, Conjecture, to
Rust. It is not feature complete, but in the long run, we are hoping to move
much of the existing functionality to Rust and rebuild Hypothesis for Python
on top of it, greatly lowering the porting effort to other languages.

Any or all of these could be turned into full fledged implementations with relatively
little effort (no more than a few months of full time work). Initial work and providing or funding ongoing maintenance efforts are required for the implementations to be viable.
