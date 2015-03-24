======================
Welcome to Hypothesis!
======================


Hypothesis is a Python library for creating unit tests which are simpler to write
and more powerful when run, finding edge cases in your code you wouldn't have
thought to look for.

Classically a unit test will usually look something like:

1. Set up some data.
2. Perform some operations on the data.
3. Assert something about the result.

With Hypothesis, tests look like

1. For all data matching some specification.
2. Perform some operations on the data.
3. Assert something about the result.

This is often called property based testing, and was popularised by the
Haskell library `Quickcheck <https://hackage.haskell.org/package/QuickCheck>`_.

Usually this takes the form of deciding on guarantees that your code should make
- properties that should always hold true, regardless of what the world throws at
you. Examples of such guarantees might be:

* Your code shouldn't throw an exception, or should only throw a particular type of exception (this works particularly well if you have a lot of internal assertions).
* If you delete an object, it is no longer visible.
* If you serialize and then deserialize a value, then you get the same value back.

Hypothesis works by generating random data matching your specification and checking
that your guarantee still holds in that case. If it finds an example where it doesn't,
it takes that example and cuts it down to size, simplifying it until it finds a
much smaller example that still causes the problem. It then saves that example in
a database, so that once it has found a problem with your code it will not forget
it in future.

This documentation is divided into a number of sections, which you can see in the sidebar (or the
menu at the top if you're on mobile), but you probably want to begin with the :doc:`Quick start guide <quickstart>`,
which will give you a worked example of how to use Hypothesis and a detailed outline
of the things you need to know to begin testing your code with it.

.. toctree::
  :maxdepth: 1
  :hidden:

  quickstart
  manifesto
  details
  extras
  examples
  internals
  community
