======================
Welcome to Hypothesis!
======================


Hypothesis is a library for creating unit tests which are simpler to write
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

Usually this takes the form of deciding on invariants, or guarantees, that your
code should satisfy and asserting that they always hold. The easiest example
of a guarantee is that for all inputs your code shouldn't throw an exception,
or should only throw a particular type of exception. Other examples of
guarantees could be things like that after removing a user from a project they
are no longer on the project, or that if you serialize and then deserialize an
object you get the same object back.

Hypothesis works by generating random data matching your specification. When it
finds an example which causes your test to fail it takes that example and cuts it
down to size, simplifying it until it finds a much smaller example that still causes
a failure. It then saves that example in a database, so that once it has found a
problem with your code it will not forget it in future.

Hypothesis is designed to be inherently unopinionated about test frameworks, and
should integrate seamlessly with your unit tests regardless of what you use.
Hypothesis just provides you with normal python functions which you can execute as
tests.

This documentation is divided into a number of sections, but you probably want to
begin with the :doc:`Quick start guide <quickstart>` for a worked example of how to
use Hypothesis and a detailed outline of the things you need to know to begin testing
your code with it.

.. toctree::
  :maxdepth: 1

  index
  quickstart
  advanced
  details
  lineage
  community
  extending
  extras
  internals
