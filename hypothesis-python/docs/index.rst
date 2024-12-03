======================
Welcome to Hypothesis!
======================

`Hypothesis <https://hypothesis.works>`_ is a Python library for
creating unit tests which are simpler to write and more powerful when run,
finding edge cases in your code you wouldn't have thought to look for. It is
stable, powerful and easy to add to any existing test suite.

It works by letting you write tests that assert that something should be true
for every case, not just the ones you happen to think of.

Think of a normal unit test as being something like the following:

1. Set up some data.
2. Perform some operations on the data.
3. Assert something about the result.

Hypothesis lets you write tests which instead look like this:

1. For all data matching some specification.
2. Perform some operations on the data.
3. Assert something about the result.

This is often called property-based testing, and was popularised by the
Haskell library `Quickcheck <https://hackage.haskell.org/package/QuickCheck>`_.

It works by generating arbitrary data matching your specification and checking
that your guarantee still holds in that case. If it finds an example where it doesn't,
it takes that example and cuts it down to size, simplifying it until it finds a
much smaller example that still causes the problem. It then saves that example
for later, so that once it has found a problem with your code it will not forget
it in the future.

Writing tests of this form usually consists of deciding on guarantees that
your code should make - properties that should always hold true,
regardless of what the world throws at you. Examples of such guarantees
might be:

* Your code shouldn't throw an exception, or should only throw a particular
  type of exception (this works particularly well if you have a lot of internal
  assertions).
* If you delete an object, it is no longer visible.
* If you serialize and then deserialize a value, then you get the same value back.

Now you know the basics of what Hypothesis does, the rest of this
documentation will take you through how and why. It's divided into a
number of sections, which you can see in the sidebar (or the
menu at the top if you're on mobile), but you probably want to begin with
the :doc:`Quick start guide <quickstart>`, which will give you a worked
example of how to use Hypothesis and a detailed outline
of the things you need to know to begin testing your code with it, or
check out some of the
`introductory articles <https://hypothesis.works/articles/intro/>`_.


.. toctree::
  :maxdepth: 1
  :hidden:
  :caption: Hypothesis

  quickstart
  details
  data
  settings
  database
  stateful
  reproducing
  ghostwriter
  examples
  extras
  django
  numpy
  observability
  supported
  changes

.. toctree::
  :maxdepth: 1
  :hidden:
  :caption: Community

  development
  manifesto
  usage
  strategies
  packaging
  community
  support
  endorsements
