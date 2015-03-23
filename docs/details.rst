============
Some details
============

~~~~~~~~
Settings
~~~~~~~~

Hypothesis tries to have good defaults for its behaviour, but sometimes that's
not enough and you need to tweak it.

The mechanism for doing this is the Settings object. You can pass this to a
@given invocation as follows:

.. code:: python

    from hypothesis import Settings

    @given(int, settings=Settings(max_examples=500))
    def test_this_thoroughly(x):
        pass

This uses a Settings object which causes the test to receive a much larger
set of examples than normal.

There is a Settings.default object. This is both a Settings object you can
use, but additionally any changes to the default object will be picked up as
the defaults for newly created settings objects.

.. code:: python

    >>> from hypothesis import Settings
    >>> s = Settings()
    >>> s.max_examples
    200
    >>> Settings.default.max_examples = 100
    >>> t = Settings()
    >>> t.max_examples
    100
    >>> s.max_examples
    200

There are a variety of other settings you can use. help(Settings) will give you
a full list of them.

Settings are also extensible. You can add new settings if you want to extend
this. This is useful for adding additional parameters for customising your
strategies. These will be picked up by all settings objects.

.. code:: python

    >>> Settings.define_setting(
    ... name="some_custom_setting", default=3,
    ... description="This is a custom settings we've just added")
    >>> s.some_custom_setting
    3


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
SearchStrategy and converting arguments
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The type of object that is used to explore the examples given to your test
function is called a SearchStrategy. The arguments to @given are passed to
the function *strategy*. This is used to convert arbitrary objects to
a SearchStrategy.

From most usage, strategy looks like a normal function:

.. code:: python

  >>> from hypothesis import strategy

  >>> strategy(int)
  RandomGeometricIntStrategy()

  >>> strategy((int, int))
  TupleStrategy((RandomGeometricIntStrategy(), RandomGeometricIntStrategy()), tuple) 

If you try to call it on something with no implementation defined you will
get a NotImplementedError:


.. code:: python

  >>> strategy(1)
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

  >>> strategy(int).example()
  192
 
  >>> strategy(str).example()
  '\U0009d5dc\U000989fc\U00106f82\U00033731'

  >>> strategy(float).example()
  -1.7551092389086e-308

  >>> strategy((int, int)).example()
  (548, 12)

Note: example is just a method that's available for this sort of interactive debugging.
It's not actually part of the process that Hypothesis uses to feed tests, though
it is of course built on the same basic mechanisms.


strategy can also accept a settings object which will customise the SearchStrategy
returned:

.. code:: python

    >>> strategy([[int]], Settings(average_list_length=0.5)).example()
    [[], [0]]

 
You can also generate lists (like tuples you generate lists from a list describing
what should be in the list rather than from the type):

.. code:: python

  >>> strategy([int]).example()
  [0, 0, -1, 0, -1, -2]

Unlike tuples, the strategy for lists will generate lists of arbitrary length.

If you have multiple elements in the list you ask for a strategy from it will
give you a mix:

.. code:: python

  >>> strategy([int, bool]).example()
  [1, True, False, -7, 35, True, -2]

There are also a bunch of custom types that let you define more specific examples.

.. code:: python

  >>> import hypothesis.descriptors as desc

  >>> strategy([desc.integers_in_range(1, 10)]).example()
  [7, 9, 9, 10, 10, 4, 10, 9, 9, 7, 4, 7, 7, 4, 7]

  In[10]: strategy([desc.floats_in_range(0, 1)]).example()
  [0.4679222775246174, 0.021441634094071356, 0.08639605748268818]

  >>> strategy(desc.one_of((float, bool))).example()
  3.6797748715455153e-281

  >>> strategy(desc.one_of((float, bool))).example()
  False


~~~~~~~~~~~~~~~~~~~
How good is assume?
~~~~~~~~~~~~~~~~~~~

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

Adding assume(all(x > 0 for x in xs)) and it passes: A sum of a list of
positive integers is positive.

The reason that this should be surprising is not that it doesn't find a
counter-example, but that it finds enough examples at all.

In order to make sure something interesting is happening, suppose we wanted to
try this for long lists. e.g. suppose we added an assume(len(xs) > 10) to it.
This should basically never find an example: A naive strategy would find fewer
than one in a thousand examples, because if each element of the list is
negative with probability half, you'd have to have ten of these go the right
way by chance. In the default configuration Hypothesis gives up long before
it's tried 1000 examples (by default it tries 200).

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
