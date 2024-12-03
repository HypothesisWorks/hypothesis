==========
Quickstart
==========

This document should talk you through everything you need to get started with
Hypothesis.

----------
An example
----------

Suppose we've written a :wikipedia:`run length encoding <Run-length_encoding>`
system and we want to test it out.

We have the following code which I took straight from the
`Rosetta Code <https://rosettacode.org/wiki/Run-length_encoding>`_ wiki (OK, I
removed some commented out code and fixed the formatting, but there are no
functional modifications):


.. code:: python

  def encode(input_string):
      count = 1
      prev = ""
      lst = []
      for character in input_string:
          if character != prev:
              if prev:
                  entry = (prev, count)
                  lst.append(entry)
              count = 1
              prev = character
          else:
              count += 1
      entry = (character, count)
      lst.append(entry)
      return lst


  def decode(lst):
      q = ""
      for character, count in lst:
          q += character * count
      return q


We want to write a test for this that will check some invariant of these
functions.

The invariant one tends to try when you've got this sort of encoding /
decoding is that if you encode something and then decode it then you get the same
value back.

Let's see how you'd do that with Hypothesis:


.. code:: python

  from hypothesis import given
  from hypothesis.strategies import text


  @given(text())
  def test_decode_inverts_encode(s):
      assert decode(encode(s)) == s

(For this example we'll just let pytest discover and run the test. We'll cover
other ways you could have run it later).

The text function returns what Hypothesis calls a search strategy. An object
with methods that describe how to generate and simplify certain kinds of
values. The :func:`@given <hypothesis.given>` decorator then takes our test
function and turns it into a
parametrized one which, when called, will run the test function over a wide
range of matching data from that strategy.

Anyway, this test immediately finds a bug in the code:

.. code::

  Falsifying example: test_decode_inverts_encode(s='')

  UnboundLocalError: local variable 'character' referenced before assignment

Hypothesis correctly points out that this code is simply wrong if called on
an empty string.

If we fix that by just adding the following code to the beginning of our ``encode`` function
then Hypothesis tells us the code is correct (by doing nothing as you'd expect
a passing test to).

.. code:: python


    if not input_string:
        return []

If we wanted to make sure this example was always checked we could add it in
explicitly by using the :obj:`@example <hypothesis.example>` decorator:

.. code:: python

  from hypothesis import example, given, strategies as st


  @given(st.text())
  @example("")
  def test_decode_inverts_encode(s):
      assert decode(encode(s)) == s

This can be useful to show other developers (or your future self) what kinds
of data are valid inputs, or to ensure that particular edge cases such as
``""`` are tested every time.  It's also great for regression tests because
although Hypothesis will :doc:`remember failing examples <database>`,
we don't recommend distributing that database.

It's also worth noting that both :obj:`@example <hypothesis.example>` and
:func:`@given <hypothesis.given>` support keyword arguments as
well as positional. The following would have worked just as well:

.. code:: python

  @given(s=st.text())
  @example(s="")
  def test_decode_inverts_encode(s):
      assert decode(encode(s)) == s

Suppose we had a more interesting bug and forgot to reset the count
each time. Say we missed a line in our ``encode`` method:

.. code:: python

  def encode(input_string):
      count = 1
      prev = ""
      lst = []
      for character in input_string:
          if character != prev:
              if prev:
                  entry = (prev, count)
                  lst.append(entry)
              # count = 1  # Missing reset operation
              prev = character
          else:
              count += 1
      entry = (character, count)
      lst.append(entry)
      return lst

Hypothesis quickly informs us of the following example:

.. code::

  Falsifying example: test_decode_inverts_encode(s='001')

Note that the example provided is really quite simple. Hypothesis doesn't just
find *any* counter-example to your tests, it knows how to simplify the examples
it finds to produce small easy to understand ones. In this case, two identical
values are enough to set the count to a number different from one, followed by
another distinct value which should have reset the count but in this case
didn't.

----------
Installing
----------

Hypothesis is :pypi:`available on PyPI as "hypothesis" <hypothesis>`. You can install it with:

.. code:: bash

  pip install hypothesis

You can install the dependencies for :doc:`optional extensions <extras>` with
e.g. ``pip install hypothesis[pandas,django]``.

If you want to install directly from the source code (e.g. because you want to
make changes and install the changed version), check out the instructions in
:gh-file:`CONTRIBUTING.rst`.

-------------
Running tests
-------------

In our example above we just let pytest discover and run our tests, but we could
also have run it explicitly ourselves:

.. code:: python

  if __name__ == "__main__":
      test_decode_inverts_encode()

We could also have done this as a :class:`python:unittest.TestCase`:

.. code:: python

  import unittest


  class TestEncoding(unittest.TestCase):
      @given(text())
      def test_decode_inverts_encode(self, s):
          self.assertEqual(decode(encode(s)), s)


  if __name__ == "__main__":
      unittest.main()

A detail: This works because Hypothesis ignores any arguments it hasn't been
told to provide (positional arguments start from the right), so the self
argument to the test is simply ignored and works as normal. This also means
that Hypothesis will play nicely with other ways of parameterizing tests. e.g
it works fine if you use pytest fixtures for some arguments and Hypothesis for
others.

-------------
Writing tests
-------------

A test in Hypothesis consists of two parts: A function that looks like a normal
test in your test framework of choice but with some additional arguments, and
a :func:`@given <hypothesis.given>` decorator that specifies
how to provide those arguments.

Here are some other examples of how you could use that:


.. code:: python

    from hypothesis import given, strategies as st


    @given(st.integers(), st.integers())
    def test_ints_are_commutative(x, y):
        assert x + y == y + x


    @given(x=st.integers(), y=st.integers())
    def test_ints_cancel(x, y):
        assert (x + y) - y == x


    @given(st.lists(st.integers()))
    def test_reversing_twice_gives_same_list(xs):
        # This will generate lists of arbitrary length (usually between 0 and
        # 100 elements) whose elements are integers.
        ys = list(xs)
        ys.reverse()
        ys.reverse()
        assert xs == ys


    @given(st.tuples(st.booleans(), st.text()))
    def test_look_tuples_work_too(t):
        # A tuple is generated as the one you provided, with the corresponding
        # types in those positions.
        assert len(t) == 2
        assert isinstance(t[0], bool)
        assert isinstance(t[1], str)


Note that as we saw in the above example you can pass arguments to :func:`@given <hypothesis.given>`
either as positional or as keywords.

--------------
Where to start
--------------

You should now know enough of the basics to write some tests for your code
using Hypothesis. The best way to learn is by doing, so go have a try.

If you're stuck for ideas for how to use this sort of test for your code, here
are some good starting points:

1. Try just calling functions with appropriate arbitrary data and see if they
   crash. You may be surprised how often this works. e.g. note that the first
   bug we found in the encoding example didn't even get as far as our
   assertion: It crashed because it couldn't handle the data we gave it, not
   because it did the wrong thing.
2. Look for duplication in your tests. Are there any cases where you're testing
   the same thing with multiple different examples? Can you generalise that to
   a single test using Hypothesis?
3. `This piece is designed for an F# implementation
   <https://fsharpforfunandprofit.com/posts/property-based-testing-2/>`_, but
   is still very good advice which you may find helps give you good ideas for
   using Hypothesis.

If you have any trouble getting started, don't feel shy about
:doc:`asking for help <community>`.
