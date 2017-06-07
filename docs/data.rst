=============================
What you can generate and how
=============================

The general philosophy of Hypothesis data generation is that everything
should be possible to generate and most things should be easy. Most things in
the standard library
is more aspirational than achieved, the state of the art is already pretty
good.

This document is a guide to what strategies are available for generating data
and how to build them. Strategies have a variety of other important internal
features, such as how they simplify, but the data they can generate is the only
public part of their API.

Functions for building strategies are all available in the hypothesis.strategies
module. The salient functions from it are as follows:

.. automodule:: hypothesis.strategies
  :members:

~~~~~~~~~~~~~~~~
Choices
~~~~~~~~~~~~~~~~

Sometimes you need an input to be from a known set of items. hypothesis gives you 2 ways to do this, choice() and sampled_from().

Examples on how to use them both are below. First up choice:

.. code:: python

    from hypothesis import given, strategies as st

    @given(user=st.text(min_size=1), service=st.text(min_size=1), choice=st.choices())
    def test_tickets(user, service, choice):
        t=choice(('ST', 'LT', 'TG', 'CT'))
        # asserts go here.

This means t will randomly be one of the items in the list ('ST', 'LT', 'TG', 'CT'). just like if you were calling random.choice() on the list.

A different, and probably better way to do this, is to use sampled_from:

.. code:: python

    from hypothesis import given, strategies as st

    @given(
        user=st.text(min_size=1), service=st.text(min_size=1),
        t=st.sampled_from(('ST', 'LT', 'TG', 'CT')))
    def test_tickets(user, service, t):
        # asserts and test code go here.

Values from sampled_from will not be copied and thus you should be careful of using mutable data. Which makes it great for the above use case, but may not always work out.

~~~~~~~~~~~~~~~~
Infinite streams
~~~~~~~~~~~~~~~~

Sometimes you need examples of a particular type to keep your test going but
you're not sure how many you'll need in advance. For this, we have streaming
types.


.. doctest::

    >>> from hypothesis.types import Stream
    >>> x = Stream(iter(integers().example, None))
    >>> # Equivalent to `streaming(integers()).example()`, which is not supported
    >>> x  # doctest: -ELLIPSIS
    Stream(...)
    >>> x[2]
    131
    >>> x  # doctest: -ELLIPSIS
    Stream(-225, 50, 131, ...)
    >>> x[10]
    127
    >>> x  # doctest: -ELLIPSIS
    Stream(-225, 50, 131, 30781241791694610923869406150329382725, 89, 62248, 107, 35771, -113, 79, 127, ...)

Think of a Stream as an infinite list where we've only evaluated as much as
we need to. As per above, you can index into it and the stream will be evaluated up to
that index and no further.

You can iterate over it too (warning: iter on a stream given to you
by Hypothesis in this way will never terminate):

.. doctest::

    >>> it = iter(x)
    >>> next(it)
    -225
    >>> next(it)
    50
    >>> next(it)
    131

Slicing will also work, and will give you back Streams. If you set an upper
bound then iter on those streams *will* terminate:

.. doctest::

    >>> list(x[:5])
    [-225, 50, 131, 30781241791694610923869406150329382725, 89]
    >>> y = x[1::2]
    >>> y  # doctest: -ELLIPSIS
    Stream(...)
    >>> y[0]
    50
    >>> y[1]
    30781241791694610923869406150329382725
    >>> y  # doctest: -ELLIPSIS
    Stream(50, 30781241791694610923869406150329382725, ...)

You can also apply a function to transform a stream:

.. doctest::

    >>> t = x[20:]
    >>> tm = t.map(lambda n: n * 2)
    >>> tm[0]
    -344
    >>> t[0]
    -172
    >>> tm  # doctest: -ELLIPSIS
    Stream(-344, ...)
    >>> t  # doctest: -ELLIPSIS
    Stream(-172, ...)

map creates a new stream where each element of the stream is the function
applied to the corresponding element of the original stream. Evaluating the
new stream will force evaluating the original stream up to that index.

(Warning: This isn't the map builtin. In Python 3 the builtin map should do
more or less the right thing, but in Python 2 it will never terminate and
will just eat up all your memory as it tries to build an infinitely long list)

These are the only operations a Stream supports. There are a few more internal
ones, but you shouldn't rely on them.

~~~~~~~~~~~~~~~~~~~
Adapting strategies
~~~~~~~~~~~~~~~~~~~

Often it is the case that a strategy doesn't produce exactly what you want it
to and you need to adapt it. Sometimes you can do this in the test, but this
hurts reuse because you then have to repeat the adaption in every test.

Hypothesis gives you ways to build strategies from other strategies given
functions for transforming the data.

-------
Mapping
-------

Map is probably the easiest and most useful of these to use. If you have a
strategy s and a function f, then an example s.map(f).example() is
f(s.example()). i.e. we draw an example from s and then apply f to it.

e.g.:

.. doctest::

  >>> lists(integers()).map(sorted).example()
  [-224, -222, 16, 159, 120699286316048]

Note that many things that you might use mapping for can also be done with the
builds function in hypothesis.strategies.

---------
Filtering
---------

filter lets you reject some examples. s.filter(f).example() is some example
of s such that f(s) is truthy.

.. doctest::

  >>> integers().filter(lambda x: x > 11).example()
  1609027033942695427531
  >>> integers().filter(lambda x: x > 11).example()
  251

It's important to note that filter isn't magic and if your condition is too
hard to satisfy then this can fail:

.. doctest::

  >>> integers().filter(lambda x: False).example()
  Traceback (most recent call last):
    ...
  hypothesis.errors.NoExamples: Could not find any valid examples in 20 tries

In general you should try to use filter only to avoid corner cases that you
don't want rather than attempting to cut out a large chunk of the search space.

A technique that often works well here is to use map to first transform the data
and then use filter to remove things that didn't work out. So for example if you
wanted pairs of integers (x,y) such that x < y you could do the following:


.. doctest::

  >>> tuples(integers(), integers()).map(
  ... lambda x: tuple(sorted(x))).filter(lambda x: x[0] != x[1]).example()
  (180, 241)

----------------------------
Chaining strategies together
----------------------------

Finally there is flatmap. Flatmap draws an example, then turns that example
into a strategy, then draws an example from *that* strategy.

It may not be obvious why you want this at first, but it turns out to be
quite useful because it lets you generate different types of data with
relationships to eachother.

For example suppose we wanted to generate a list of lists of the same
length:

.. code-block:: pycon

  >>> rectangle_lists = integers(min_value=0, max_value=10).flatmap(
  ... lambda n: lists(lists(integers(), min_size=n, max_size=n)))
  >>> find(rectangle_lists, lambda x: True)
  []
  >>> find(rectangle_lists, lambda x: len(x) >= 10)
  [[], [], [], [], [], [], [], [], [], []]
  >>> find(rectangle_lists, lambda t: len(t) >= 3 and len(t[0]) >= 3)
  [[0, 0, 0], [0, 0, 0], [0, 0, 0]]
  >>> find(rectangle_lists, lambda t: sum(len(s) for s in t) >= 10)
  [[0], [0], [0], [0], [0], [0], [0], [0], [0], [0]]

In this example we first choose a length for our tuples, then we build a
strategy which generates lists containing lists precisely of that length. The
finds show what simple examples for this look like.

Most of the time you probably don't want flatmap, but unlike filter and map
which are just conveniences for things you could just do in your tests,
flatmap allows genuinely new data generation that you wouldn't otherwise be
able to easily do.

(If you know Haskell: Yes, this is more or less a monadic bind. If you don't
know Haskell, ignore everything in these parentheses. You do not need to
understand anything about monads to use this, or anything else in Hypothesis).


--------------
Recursive data
--------------

Sometimes the data you want to generate has a recursive definition. e.g. if you
wanted to generate JSON data, valid JSON is:

1. Any float, any boolean, any unicode string.
2. Any list of valid JSON data
3. Any dictionary mapping unicode strings to valid JSON data.

The problem is that you cannot call a strategy recursively and expect it to not just
blow up and eat all your memory.  The other problem here is that not all unicode strings
display consistently on different machines, so we'll restrict them in our doctest.

The way Hypothesis handles this is with the ':py:func:`recursive` function
which you pass in a base case and a function that given a strategy for your data type
returns a new strategy for it. So for example:

.. doctest::

  >>> from string import printable; from pprint import pprint
  >>> json = recursive(none() | booleans() | floats() | text(printable),
  ... lambda children: lists(children) | dictionaries(text(printable), children))
  >>> pprint(json.example())
  {'': 'Me$',
   "\r5qPZ%etF:vL'9gC": False,
   '$KsT(( J/(wQ': [],
   '0)G&31': False,
   '7': [],
   'C.i]A-I': {':?Xh>[;': None,
               'YHT\r!\x0b': -6.801160220000663e+18,
  ...
  >>> pprint(json.example())
  [{"7_8'qyb": None,
    ':': -0.3641507440748771,
    'TI_^\n>L{T\x0c': -0.0,
    'ZiOqQ\t': 'RKT*a]IjI/Zx2HB4ODiSUN)LsZ',
    'n;E^^6|9=@g@@BmAi': '7j5\\'},
   True]
  >>> pprint(json.example())
  []

That is, we start with our leaf data and then we augment it by allowing lists and dictionaries of anything we can generate as JSON data.

The size control of this works by limiting the maximum number of values that can be drawn from the base strategy. So for example if
we wanted to only generate really small JSON we could do this as:


.. doctest::

  >>> small_lists = recursive(booleans(), lists, max_leaves=5)
  >>> small_lists.example()
  True
  >>> small_lists.example()
  [True, False]
  >>> small_lists.example()
  True

~~~~~~~~~~~~~~~~~~~~
Composite strategies
~~~~~~~~~~~~~~~~~~~~

The @composite decorator lets you combine other strategies in more or less
arbitrary ways. It's probably the main thing you'll want to use for
complicated custom strategies.

The composite decorator works by giving you a function as the first argument
that you can use to draw examples from other strategies. For example, the
following gives you a list and an index into it:

.. doctest::

    >>> @composite
    ... def list_and_index(draw, elements=integers()):
    ...     xs = draw(lists(elements, min_size=1))
    ...     i = draw(integers(min_value=0, max_value=len(xs) - 1))
    ...     return (xs, i)

'draw(s)' is a function that should be thought of as returning s.example(),
except that the result is reproducible and will minimize correctly. The
decorated function has the initial argument removed from the list, but will
accept all the others in the expected order. Defaults are preserved.

.. doctest::

    >>> list_and_index()
    list_and_index()
    >>> list_and_index().example()
    ([215, 112], 0)

    >>> list_and_index(booleans())
    list_and_index(elements=booleans())
    >>> list_and_index(booleans()).example()
    ([False, False], 1)

Note that the repr will work exactly like it does for all the built-in
strategies: It will be a function that you can call to get the strategy in
question, with values provided only if they do not match the defaults.

You can use assume inside composite functions:

.. code-block:: python

    @composite
    def distinct_strings_with_common_characters(draw):
        x = draw(text(), min_size=1)
        y = draw(text(alphabet=x))
        assume(x != y)
        return (x, y)

This works as assume normally would, filtering out any examples for which the
passed in argument is falsey.


.. _interactive-draw:

~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Drawing interactively in tests
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

There is also the ``data()`` strategy, which gives you a means of using
strategies interactively. Rather than having to specify everything up front in
``@given`` you can draw from strategies in the body of your test:

.. code-block:: python

    @given(data())
    def test_draw_sequentially(data):
        x = data.draw(integers())
        y = data.draw(integers(min_value=x))
        assert x < y

If the test fails, each draw will be printed with the falsifying example. e.g.
the above is wrong (it has a boundary condition error), so will print:

.. code-block:: pycon

    Falsifying example: test_draw_sequentially(data=data(...))
    Draw 1: 0
    Draw 2: 0

As you can see, data drawn this way is simplified as usual.

Test functions using the ``data()`` strategy do not support explicit
``@example(...)``s.  In this case, the best option is usually to construct
your data with ``@composite`` or the explicit example, and unpack this within
the body of the test.

Optionally, you can provide a label to identify values generated by each call
to ``data.draw()``.  These labels can be used to identify values in the output
of a falsifying example.

For instance:

.. code-block:: python

    @given(data())
    def test_draw_sequentially(data):
        x = data.draw(integers(), label='First number')
        y = data.draw(integers(min_value=x), label='Second number')
        assert x < y

will produce the output:

.. code-block:: pycon

    Falsifying example: test_draw_sequentially(data=data(...))
    Draw 1 (First number): 0
    Draw 2 (Second number): 0
