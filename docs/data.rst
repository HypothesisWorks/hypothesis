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

.. code-block:: pycon

  >>> lists(integers()).map(sorted).example()
  [1, 5, 17, 21, 24, 30, 45, 82, 88, 88, 90, 96, 105]

Note that many things that you might use mapping for can also be done with the
builds function in hypothesis.strategies.

---------
Filtering
---------

filter lets you reject some examples. s.filter(f).example() is some example
of s such that f(s) is truthy.

.. code-block:: pycon

  >>> integers().filter(lambda x: x > 11).example()
  1873
  >>> integers().filter(lambda x: x > 11).example()
  73

It's important to note that filter isn't magic and if your condition is too
hard to satisfy then this can fail:

.. code-block:: pycon

  >>> integers().filter(lambda x: False).example()
  Traceback (most recent call last):
    File "<stdin>", line 1, in <module>
    File "/home/david/projects/hypothesis/src/hypothesis/searchstrategy/strategies.py", line 175, in example
      'Could not find any valid examples in 20 tries'
  hypothesis.errors.NoExamples: Could not find any valid examples in 20 tries

In general you should try to use filter only to avoid corner cases that you
don't want rather than attempting to cut out a large chunk of the search space.

A technique that often works well here is to use map to first transform the data
and then use filter to remove things that didn't work out. So for example if you
wanted pairs of integers (x,y) such that x < y you could do the following:


.. code-block:: pycon

  >>> tuples(integers(), integers())).map(
  ... lambda x: tuple(sorted(x))).filter(lambda x: x[0] != x[1]).example()
  (42, 1281698)

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

  >>> from hypothesis.strategies import integers, lists
  >>> from hypothesis import find
  >>> rectangle_lists = integers(min_value=0, max_value=10).flatmap(lambda n:
  ... lists(lists(integers(), min_size=n, max_size=n)))
  >>> find(rectangle_lists, lambda x: True)
  []
  >>> find(rectangle_lists, lambda x: len(x) >= 10)
  [[], [], [], [], [], [], [], [], [], []]
  >>> find(rectangle_lists, lambda t: len(t) >= 3 and len(t[0])  >= 3)
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
blow up and eat all your memory.

The way Hypothesis handles this is with the 'recursive' function in hypothesis.strategies
which you pass in a base case and a function that given a strategy for your data type
returns a new strategy for it. So for example:

.. code-block:: pycon

  >>> import hypothesis.strategies as st
  >>> json = st.recursive(st.floats() | st.booleans() | st.text() | st.none(),
  ... lambda children: st.lists(children) | st.dictionaries(st.text(), children))
  >>> json.example()
  {'': None, '\U000b3407\U000b3407\U000b3407': {
      '': '"é""é\x11', '\x13': 1.6153068016570349e-282,
      '\x00': '\x11\x11\x11"\x11"é"éé\x11""éé"\x11"éé\x11éé\x11é\x11',
    '\x80': 'é\x11\x11\x11\x11\x11\x11', '\x13\x13\x00\x80\x80\x00': 4.643602465868519e-144
    }, '\U000b3407': None}
  >>> json.example()
  []
  >>> json.example()
  '\x06ě\U000d25e4H\U000d25e4\x06ě'

That is, we start with our leaf data and then we augment it by allowing lists and dictionaries of anything we can generate as JSON data.

The size control of this works by limiting the maximum number of values that can be drawn from the base strategy. So for example if
we wanted to only generate really small JSON we could do this as:


.. code-block:: pycon

  >>> small_lists = st.recursive(st.booleans(), st.lists, max_leaves=5)
  >>> small_lists.example()
  False
  >>> small_lists.example()
  [[False], [], [], [], [], []]
  >>> small_lists.example()
  False
  >>> small_lists.example()
  []

~~~~~~~~~~~~~~~~~~~~
Composite strategies
~~~~~~~~~~~~~~~~~~~~

The @composite decorator lets you combine other strategies in more or less
arbitrary ways.

Advance warning: You're going to end up wanting to use this API for a lot of
things, and it's not that you *shouldn't* do that, but it has certain
intrinsic limitations which mean that overuse of it can hurt performance and
example quality.

If it's convenient to do so you should use builds instead. Otherwise feel free
to use this, and if you end up with bad examples or poor performance then you
should look here first as the culprit.

The composite decorator works by giving you a function as the first argument
that you can use to draw examples from other strategies. For example, the
following gives you a list and an index into it:

.. code-block:: python

    @composite
    def list_and_index(draw, elements=integers()):
        xs = draw(lists(elements, min_size=1))
        i = draw(integers(min_value=0, max_value=len(xs) - 1))
        return (xs, i)

'draw(s)' is a function that should be thought of as returning s.example(),
except that the result is reproducible and will minimize correctly. The
decorated function has the initial argument removed from the list, but will
accept all the others in the expected order. Defaults are preserved.

.. code-block:: pycon

    >>> list_and_index()
    list_and_index()
    >>> list_and_index().example()
    ([5585, 4073], 1)

    >>> list_and_index(booleans())
    list_and_index(elements=booleans())
    >>> list_and_index(booleans()).example()
    ([False, False, True], 1)

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
