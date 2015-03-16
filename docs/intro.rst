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

Suppose we've written a `run length encoding <http://en.wikipedia.org/wiki/Run-length_encoding>`_ system and we want to test it out.

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


~~~~~~~~~~~~~~~~~~~~~~~~~
Random data in my tests??
~~~~~~~~~~~~~~~~~~~~~~~~~

Randomization in tests has a bad reputation - unreliable CI runs are the worst, and
randomness seems like the very definition of unreliable.

Hypothesis has two defences against this problem:

1. Hypothesis can only ever exhibit false negatives - a test can fail to find an example,
and thus pass when it should fail, but if a test fails then it is demonstrating a genuine
bug. So if your build fails randomly it's still telling you about a new bug you hadn't
previously seen.
2. Hypothesis saves failing examples in a database, so once a test starts failing it should
keep failing, because Hypothesis remembers the previous example and tries that first.

If that's not enough for you, you can also set the derandomize setting to True, which will
cause all tests to be run with a random number generator seeded off the function body. I
don't particularly recommend it - it significantly decreases the potential for Hypothesis
to find interesting bugs because each time you run your tests it always checks the same
set of examples - but it's a perfectly good approach if you need a 100% deterministic test
suite.

~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
SearchStrategy and converting arguments
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The type of object that is used to explore the examples given to your test
function is called a SearchStrategy. The arguments to @given are passed to
the function *strategy*. This is used to convert arbitrary objects to
a SearchStrategy.

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

Although we have a strategy for producing ints it doesn't make sense to convert
an *individual* int into a strategy.

Conversely there's no implementation for the type "tuple" because we need to know
the shape of the tuple and what sort of elements to put in it:

.. code:: python

  In[5]: strategy(tuple)
  NotImplementedError: No implementation available for <class 'tuple'>


The general idea is that arguments to strategy should "look like types" and
should generate things that are instances of that type. With collections and
similar you also need to specify the types of the elements. So e.g. the
strategy you get for (int, int, int) is a strategy for generating triples
of ints.

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
 

You can also generate lists (like tuples you generate lists from a list describing
what should be in the list rather than from just the type list):

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


~~~~~~~~~~~~~~~~~~~~~
Extending a function?
~~~~~~~~~~~~~~~~~~~~~

The way this works is that Hypothesis has something that looks suspiciously
like its own object system, called ExtMethod.

It mirrors the Python object system as closely as possible and has the
same method resolution order, but allows for methods that are defined externally
to the class that uses them. This allows extensibly doing different things
based on the type of an argument without worrying about the namespacing problems
caused by MonkeyPatching.

strategy is the main ExtMethod you are likely to interact with directly, but
there are a number of others that Hypothesis uses under the hood.


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
  

Hypothesis has an adaptive exploration strategy to try to avoid things which falsify
assumptions, which should generally result in it still being able to find examples in hard
to find situations.

Suppose we had the following:


.. code:: python

  @given([int])
  def test_sum_is_positive(xs):
    assert sum(xs) > 0

Unsurprisingly this fails and gives the falsifying example [].

Adding assume(xs) to this removes the trivial empty example and gives us [0].

Adding assume(all(x > 0 for x in xs)) and, unsurprisingly, it passes.

This may seem obvious, and indeed it is, but suppose we wanted to try this for long
lists. e.g. suppose we added an assume(len(xs) > 10) to it. This should basically
never find an example: A naive strategy would find fewer than one in a thousand
examples, and in the default configuration Hypothesis gives up long before it's
tried 1000 examples (by default it tries 200).

Here's what happens if we try to run this:


.. code:: python

  @given([int])
  def test_sum_is_positive(xs):
      assume(len(xs) > 10)
      assume(all(x > 0 for x in xs))
      print(xs)
      assert sum(xs) > 0

  In: test_sum_is_positive()
  [17, 12, 7, 13, 11, 3, 6, 9, 8, 11, 47, 27, 1, 31, 1]
  [6, 2, 29, 30, 25, 34, 19, 15, 50, 16, 10, 3, 16]
  [25, 17, 9, 19, 15, 2, 2, 4, 22, 10, 10, 27, 3, 1, 14, 17, 13, 8, 16, 9, 2, 26, 5, 18, 16, 4]
  [17, 65, 78, 1, 8, 29, 2, 79, 28, 18, 39]
  [13, 26, 8, 3, 4, 76, 6, 14, 20, 27, 21, 32, 14, 42, 9, 24, 33, 9, 5, 15, 30, 40, 58, 2, 2, 4, 40, 1, 42, 33, 22, 45, 51, 2, 8, 4, 11, 5, 35, 18, 1, 46]
  [2, 1, 2, 2, 3, 10, 12, 11, 21, 11, 1, 16]

As you can see, Hypothesis doesn't find *many* examples here, but it finds some - enough to
keep it happy.

In general if you *can* shape your strategies better to your tests you should - for example
integers_in_range(1, 1000) is a lot better than assume(1 <= x <= 1000), but assume will take
you a long way if you can't.

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

------
Extras
------

Hypothesis has a zero dependency policy for the core library. For things which need a
dependency to work, these are farmed off into extra packages on pypi.

These end up putting any additional things you need to import (if there are any) under
the hypothesis.extra namespace.

~~~~~~~~~~~~~~~~~~~
hypothesis-datetime
~~~~~~~~~~~~~~~~~~~

As might be expected, this adds support for datetime to Hypothesis.

If you install the hypothesis-datetime package then you get a strategy for datetime
out of the box:

.. code:: python

  In [1]: from datetime import datetime
  In [2]: from hypothesis import strategy

  In [3]: strategy(datetime).example()
  Out[3]: datetime.datetime(6360, 1, 3, 12, 30, 56, 185849)

  In [4]: strategy(datetime).example()
  Out[4]: datetime.datetime(6187, 6, 11, 0, 0, 23, 809965, tzinfo=<UTC>)

  In [5]: strategy(datetime).example()
  Out[5]: datetime.datetime(4076, 8, 7, 0, 15, 55, 127297, tzinfo=<DstTzInfo 'Turkey' EET+2:00:00 STD>)

So things like the following work:

.. code:: python

  @given(datetime)
  def test_365_days_are_one_year(d):
      assert (d + timedelta(days=365)).year > d.year


Or rather, the test correctly fails:

.. 

  Falsifying example: test_add_one_year(d=datetime.datetime(2000, 1, 1, 0, 0, tzinfo=<UTC>))

We forgot about leap years.

(Note: Actually most of the time you run that test it will pass because Hypothesis does not hit
January 1st on a leap year with high enough probability that it will often find it.
However the advantage of the Hypothesis database is that once this example is found
it will stay found)

We can also restrict ourselves to just naive datetimes or just timezone aware
datetimes.


.. code:: python

  from hypothesis.extra.datetime import naive_datetime, timezone_aware_datetime

  @given(naive_datetime)
  def test_naive_datetime(xs):
    assert isinstance(xs, datetime)
    assert xs.tzinfo is None

  @given(timezone_aware_datetime)
  def test_non_naive_datetime(xs):
    assert isinstance(xs, datetime)
    assert xs.tzinfo is not None


Both of the above will pass.

~~~~~~~~~~~~~~~~~~~~~~
hypothesis-fakefactory
~~~~~~~~~~~~~~~~~~~~~~

`Fake-factory <https://pypi.python.org/pypi/fake-factory>`_ is another Python
library for data generation. hypothesis-fakefactory is a package which lets you
use fake-factory generators to parametrize tests.

In hypothesis.extra.fakefactory it defines the type FakeFactory which is a
placeholder for producing data from any FakeFactory type.

So for example the following will parametrize a test by an email address:


.. code:: python

  @given(FakeFactory('email'))
  def test_email(email):
      assert '@' in email


Naturally you can compose these in all the usual ways, so e.g.

.. code:: python

  In [1]: from hypothesis.extra.fakefactory import FakeFactory
  In [2]: from hypothesis import strategy
  In [3]: strategy([FakeFactory('email')]).example()
  Out[3]: 
  ['.@.com',
   '.@yahoo.com',
   'kalvelis.paulius@yahoo.com',
   'eraslan.mohsim@demirkoruturk.info']

You can also specify locales:


.. code:: python

  In [4]: strategy(FakeFactory('name', locale='en_US')).example()
  Out[4]: 'Kai Grant'

  In [5]: strategy(FakeFactory('name', locale='fr_FR')).example()
  Out[5]: 'Édouard Paul'

Or if you want you can specify several locales:

.. code:: python

  In [6]: strategy([FakeFactory('name', locales=['en_US', 'fr_FR'])]).example()
  Out[6]: 
  ['Michel Blanchet',
   'Victor Collin',
   'Eugène Perrin',
   'Miss Bernice Satterfield MD']

If you want to your own FakeFactory providers you can do that too, passing them
in as a providers argument to the FakeFactory type. It will generally be more
powerful to use Hypothesis's custom strategies though unless you have a specific
existing provider you want to use.

~~~~~~~~~~~~~~~~~
hypothesis-pytest
~~~~~~~~~~~~~~~~~

hypothesis-pytest is the world's most basic pytest plugin. Install it to get
slightly better integrated example reporting when using @given and running
under pytest. That's basically all it does.

-------------------------------------------
Integrating Hypothesis with your test suite
-------------------------------------------

Hypothesis is very unopinionated about how you run your tests because all it does is modify your test functions.
You can use it on the tests you want without affecting any others.

It certainly works fine with pytest, nose and unittest and should work fine with anything else.

There *is* `a pytest plugin <https://pypi.python.org/pypi/hypothesis-pytest>`_, which if you're using Hypothesis
with pytest you should probably use, but it's not strictly necessary - its purely for improving the quality of the
reporting a bit (by default Hypothesis prints its falsifying examples to stdout).
