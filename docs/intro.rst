==============================
 An introduction to Hypothesis
==============================

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

Usually this takes the form of deciding on invariants that your code should satisfy
and asserting that they always hold, but you can also just modify your existing unit
tests to be a bit more general.

----------
An example
----------

Suppose we've written a run length encoding system and we want to test it out.

We have the following code which I took straight from the
`Rosetta Code <http://rosettacode.org/wiki/Run-length_encoding>`_ wiki (OK, I removed some commented out code and fixed the formatting, but there
are no functional modifications):


.. code:: python

  def encode(input_string):
      count = 1
      prev = ''
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
      else:
          entry = (character, count)
          lst.append(entry)
      return lst


  def decode(lst):
      q = ''
      for character, count in lst:
          q += character * count
      return q


We want to write a test for this that will check some invariant of these functions.

The obvious invariant one tends to try when you've got this sort of encoding / decoding
is that if you encode something and then decode it you get the same value back.

Lets see how you'd do that with Hypothesis:


.. code:: python

  @given(str)
  def test_decode_inverts_encode(s):
      assert decode(encode(s)) == s


You can either let pytest discover that or if you just run it explicitly yourself:

.. code:: python

  if __name__ == '__main__':
      test_decode_inverts_encode()

You could also have done this as a unittest TestCase:


.. code:: python

  import unittest


  class TestEncoding(unittest.TestCase):
      @given(str)
      def test_decode_inverts_encode(self, s):
          self.assertEqual(decode(encode(s)), s)

  if __name__ == '__main__':
      unittest.main()

The @given decorator takes our test function and turns it into a parametrized one.
If it's called as normal by whatever test runner you like (or just explicitly called
with no arguments) then Hypothesis will turn it into a parametrized test over a wide
range of data.

Anyway, this test immediately finds a bug in the code:

..

  Falsifying example: test_decode_inverts_encode(s='')
  UnboundLocalError: local variable 'character' referenced before assignment

Hypothesis correctly points out that this code is simply wrong if called on
an empty string.

If we fix that by just adding the following code to the beginning of the function
then Hypothesis tells us the code is correct (by doing nothing as you'd expect
a passing test to).

.. code:: python

  
    if not input_string:
        return []


Suppose we had a more interesting bug and forgot to reset the count each time.

Hypothesis quickly informs us of the following example:

..

  Falsifying example: test_decode_inverts_encode(s='001')

Note that the example provided is really quite simple. Hypothesis doesn't just
find *any* counter-example to your tests, it knows how to simplify the examples
it finds to produce small easy to understand examples. In this case, two identical
values are enough to set the count to a number different from one, followed by another
distinct value which shold have reset the count but in this case didn't.

Some side notes:
  
* The examples Hypothesis provides are valid Python code you can run. When called with the arguments explicitly provided the test functions Hypothesis uses are just calls to the underlying test function)
* We actually got lucky with the above run. Hypothesis almost always finds a counter-example, but it's not usually quite such a nice one. Other example that Hypothesis could have found are things like 'aa0', '110', etc. The simplification process only simplifies one character at a time.
* Because of the use of str this behaves differently in python 2 and python 3. In python 2 the example would have been something like '\x02\x02\x00' because str is a binary type. Hypothesis works equally well in both python 2 and python 3, but if you want consistent behaviour across the two you need something like `six <https://pypi.python.org/pypi/six>`_'s text_type. 


----------------
How @given works
----------------

Hypothesis takes the arguments provided to @given and uses them to come up with
a strategy for providing data to your test function. It calls the same function
many times - initially with random data and then, if the first stage found an
example which causes it to error, with increasingly simple versions of the same
example until it finds an example triggering the failure that is as small as possible.

The latter is very much a greedy local search method so is not guaranteed to find
the simplest possible example, but generally speaking the examples it finds are very
easy to understand.

~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
SearchStrategy and converting arguments
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The type of object that is used to explore the examples given to your test
function is called a SearchStrategy. The arguments to @given are passed to
the function *strategy*. This is used to convert arbitrary objects to
a SearchStrategy.

The way this works is that Hypothesis has something that looks suspiciously
like its own object system, called ExtMethod.

It mirrors the Python object system as closely as possible and has the
same method resolution order, but allows for methods that are defined externally
to the class that uses them. This allows extensibly doing different things
based on the type of an argument without worrying about the namespacing problems
caused by MonkeyPatching.

strategy is the main ExtMethod you are likely to interact with directly, but
there are a number of others that Hypothesis uses under the hood.

From most usage, strategy looks like a normal function:

.. code:: python

  In [1]: from hypothesis import strategy

  In [2]: strategy(int)
  Out[2]: RandomGeometricIntStrategy(int)

  In [3]: strategy((int, int, int))
  Out[3]: TupleStrategy((int, int, int))

If you try to call it on something with no implementation defined you will
get a NotImplementedError:


.. code:: python

  In [4]: strategy(1)
  NotImplementedError: No implementation available for 1

  In[5]: strategy(tuple)
  NotImplementedError: No implementation available for <class 'tuple'>


Note that we could call strategy with the type 'int' but not with individual
ints. Similarly we can call it with tuples but not type 'tuple'. The general
idea is that arguments to strategy should "look like types" and should generate
things that are instances of that type. With collections and similar you also
need to specify the types of the elements. So e.g. the strategy you get for
(int, int, int) is a strategy for generating triples of ints.

If you want to see the sort of data that a strategy produces you can ask it
for an example:

.. code:: python

  In [2]: strategy(int).example()
  Out[2]: 192
 
  In [3]: strategy(str).example()
  Out[3]: '\U0009d5dc\U000989fc\U00106f82\U00033731'

  In [4]: strategy(float).example()
  Out[4]: -1.7551092389086e-308

  In [5]: strategy((int, int)).example()
  Out[5]: (548, 12)
 

You can also generate lists:

.. code:: python

  In [6]: strategy([int]).example()
  Out[6]: [0, 0, -1, 0, -1, -2]

Unlike tuples, the strategy for lists will generate lists of arbitrary length.

If you have multiple elements in the list you ask for a strategy from it will
give you a mix:

.. code:: python

  In [7]: strategy([int, bool]).example()
  Out[7]: [1, True, False, -7, 35, True, -2]

There are also a bunch of custom types that let you define more specific examples.

.. code:: python

  In [8]: import hypothesis.descriptors as desc

  In [9]: strategy([desc.integers_in_range(1, 10)]).example()
  Out[9]: [7, 9, 9, 10, 10, 4, 10, 9, 9, 7, 4, 7, 7, 4, 7]

  In[10]: strategy([desc.floats_in_range(0, 1)]).example()
  Out[10]: [0.4679222775246174, 0.021441634094071356, 0.08639605748268818]

  In [11]: strategy(desc.one_of((float, bool))).example()
  Out[11]: 3.6797748715455153e-281

  In [12]: strategy(desc.one_of((float, bool))).example()
  Out[12]: False

You can build new strategies out of other strategies. For example:

.. code:: python

  In [13]: strategy(int).map(pack=Decimal, descriptor=Decimal).example()
  Out[13]: Decimal('6029418')
  

This is generally the encouraged way to do it: The details of how SearchStrategy
works are not currently considered part of the public API and may be liable to
change.

If you want to register this so that strategy works for your custom types you
can do this by extending the strategy method:

.. code:: python

  In [14]: @strategy.extend_static(Decimal)
     ....: def decimal_strategy(d, settings):
     ....:     return strategy(int, settings).map(pack=Decimal, descriptor=Decimal)
     ....: 

  In [15]: strategy(Decimal).example()
  Out[15]: Decimal('13')


You can also define types for your own custom data generation if you need something
more specific. For example here is a strategy that lets you specify the exact length
of list you want:

.. code:: python

  In [16]: from collections import namedtuple
  In [17]: ListsOfFixedLength = namedtuple('ListsOfFixedLength', ('length', 'elements'))
  In [18]: @strategy.extend(ListsOfFixedLength)
     ....: def fixed_length_lists_strategy(descriptor, settings):
     ....:     return strategy((descriptor.elements,) * descriptor.length, settings).map(
     ....:        pack=list, descriptor=descriptor)
     ....: 
  In [19]: strategy(ListsOfFixedLength(5, int)).example()
  Out[19]: [0, 2190, 899, 2, -1326]

(You don't have to use namedtuple for this, but I tend to because they're
convenient)

Note: example is just a method that's available for this sort of interactive debugging.
It's not actually part of the process that Hypothesis uses to feed tests, though
it is of course built off the same infrastructure.


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
The gory details of given parameters
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The @given decorator may be used to specify what arguments of a function should
be parametrized over. You can use either positional or keyword arguments or a mixture
of the two.

For example all of the following are valid uses:

.. code:: python

  @given(int, int)
  def a(x, y):
    pass

  @given(int, y=int)
  def b(x, y):
    pass

  @given(int)
  def c(x, y):
    pass

  @given(y=int)
  def d(x, y):
    pass

  @given(x=int, y=int)
  def e(x, \*\*kwargs):
    pass


  class SomeTest(TestCase):
      @given(int)
      def test_a_thing(self, x):
          pass

The following are not:

.. code:: python

  @given(int, int, int)
  def e(x, y):
      pass

  @given(x=int)
  def f(x, y):
      pass

  @given()
  def f(x, y):
      pass


The rules for determining what are valid uses of given are as follows:

1. Arguments passed as keyword arguments must cover the right hand side of the argument list
2. Positional arguments fill up from the right, starting from the first argument not covered by a keyword argument.
3. If the function has kwargs, additional arguments will be added corresponding to any keyword arguments passed. These will be to the right of the normal argument list in an arbitrary order.
4. varargs are forbidden on functions used with @given

If you don't have kwargs then the function returned by @given will have the same argspec (i.e. same arguments, keyword arguments, etc) as the original but with different defaults.

The reason for the "filling up from the right" behaviour is so that using @given with instance methods works: self will be passed to the function as normal and not be parametrized over.

If all this seems really confusing, my recommendation is to just use keyword arguments for everything.

-------------------------------------------
Integrating Hypothesis with your test suite
-------------------------------------------

Hypothesis is very unopinionated about how you run your tests because all it does is modify your test functions.
You can use it on the tests you want without affecting any others.

It certainly works fine with pytest, nose and unittest and should work fine with anything else.

There *is* `a pytest plugin <https://pypi.python.org/pypi/hypothesis-pytest>`_, which if you're using Hypothesis
with pytest you should probably use, but it's not strictly necessary - its purely for improving the quality of the
reporting a bit (by default Hypothesis prints its falsifying examples to stdout).
