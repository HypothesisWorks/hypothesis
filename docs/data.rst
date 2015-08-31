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
Infinite streams
~~~~~~~~~~~~~~~~

Sometimes you need examples of a particular type to keep your test going but
you're not sure how many you'll need in advance. For this, we have streaming
types.


.. code-block:: python

    >>> from hypothesis import strategy
    >>> from hypothesis.strategies import streaming, integers
    >>> x = strategy(streaming(integers())).example()
    >>> x
    Stream(...)
    >>> x[2]
    209
    >>> x
    Stream(32, 132, 209, ...)
    >>> x[10]
    130
    >>> x
    Stream(32, 132, 209, 843, -19, 58, 141, -1046, 37, 243, 130, ...)

Think of a Stream as an infinite list where we've only evaluated as much as
we need to. As per above, you can index into it and the stream will be evaluated up to
that index and no further.

You can iterate over it too (warning: iter on a stream given to you
by Hypothesis in this way will never terminate):

.. code-block:: python

    >>> it = iter(x)
    >>> next(it)
    32
    >>> next(it)
    132
    >>> next(it)
    209
    >>> next(it)
    843

Slicing will also work, and will give you back Streams. If you set an upper
bound then iter on those streams *will* terminate:

.. code-block:: python

    >>> list(x[:5])
    [32, 132, 209, 843, -19]
    >>> y = x[1::2]
    >>> y
    Stream(...)
    >>> y[0]
    132
    >>> y[1]
    843
    >>> y
    Stream(132, 843, ...)

You can also apply a function to transform a stream:

.. code-block:: python

    >>> t = strategy(streaming(int)).example()
    >>> tm = t.map(lambda n: n * 2)
    >>> tm[0]
    26
    >>> t[0]
    13
    >>> tm
    Stream(26, ...)
    >>> t
    Stream(13, ...)

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

.. code-block:: python

  >>> strategy([int]).map(sorted).example()
  [1, 5, 17, 21, 24, 30, 45, 82, 88, 88, 90, 96, 105]

Note that many things that you might use mapping for can also be done with the
builds function in hypothesis.strategies.

---------
Filtering
---------

filter lets you reject some examples. s.filter(f).example() is some example
of s such that f(s) is truthy.

.. code-block:: python

  >>> strategy(int).filter(lambda x: x > 11).example()
  1873
  >>> strategy(int).filter(lambda x: x > 11).example()
  73

It's important to note that filter isn't magic and if your condition is too
hard to satisfy then this can fail:

.. code-block:: python

  >>> strategy(int).filter(lambda x: False).example()
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


.. code-block:: python

  >>> strategy((int, int)).map(
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


.. code-block:: python

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

.. code-block:: python

  >>> import hypothesis.strategies as st
  >>> json = st.recursive(st.floats() | st.booleans() | st.text() | st.none(),
    lambda children: st.lists(children) | st.dictionaries(st.text(), children))
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


.. code-block:: python

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

.. code-block:: python

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

~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Defining entirely new strategies
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The full SearchStrategy API is only "semi-public", in that it may (but usually
won't) break between minor versions but won't break between patch releases.

However Hypothesis exposes a simplified version of the interface that you can
use to build pretty good strategies. In general it's pretty strongly recommended
that you don't use this if you can build your strategy out of existing ones,
but it works perfectly well.

Here is an example of using the simplified interface:

.. code:: python

  from hypothesis.searchstrategy import BasicStrategy


  class Bitfields(BasicStrategy):

      """A BasicStrategy for generating 128 bit integers to be treated as if they
      were bitfields."""

      def generate_parameter(self, random):
          # This controls the shape of the data that can be generated by
          # randomly screening off some bits.
          return random.getrandbits(128)

      def generate(self, random, parameter_value):
          # This generates a random value subject to a parameter we have
          # previously generated
          return parameter_value & random.getrandbits(128)

      def simplify(self, random, value):
          # Simplify by settings bits to zero.
          for i in range(128):
              k = 1 << i
              # It's important to test this because otherwise it would create a
              # cycle where value simplifies to value. This would cause
              # Hypothesis to get stuck on that value and not be able to simplify
              # it further.
              if value & k:
                  yield value & (~k)

      def copy(self, value):
          # integers are immutable so there's no need to copy them
          return value


Only generate is strictly necessary to implement. copy will default to using
deepcopy, generate_parameter will default to returning None, and simplify will
default to not simplifying.

The reason why the parameters are important is that they let you "shape" the
data so that it works with adaptive assumptions, which work by being more likely
to reuse parameter values that don't cause assumptions to be violated.

Simplify is of course what Hypothesis uses to produce simpler examples. It will
greedily apply it to your data to produce the simplest example it possible can.
You should avoid having cycles or unbounded paths in the graph, as this will tend
to hurt example quality and performance.

Instances of BasicStrategy are not actually strategies and must be converted
to them using the basic function from hypothesis.strategies. You can convert
either a class or an instance:

.. code:: python

  >>> basic(Bitfields).example()
  70449389301502165026254673882738917538
  >>> strategy(Bitfields()).example()
  180947746395888412520415493036267606532

You can also skip the class definition if you prefer and just pass functions to
basic. e.g.

.. code:: python

  >>> basic(generate=lambda random, _: random.getrandbits(8)).example()
  88

The arguments to basic have the same names as the methods you would define on
BasicStrategy.

Caveats:

* Remember that BasicStrategy is not a subclass of SearchStrategy, only
  convertible to one.
* The values produced by BasicStrategy are opaque to Hypothesis in a way that
  ones it is more intimately familiar with are not, because it's impossible
  to safely and sensibly deduplicate arbitrary Python objects. This is mostly
  fine but it blocks certain heuristics and optimisations Hypothesis uses for
  improving the simplification process. As such implementations using
  BasicStrategy might get slightly worse examples than the equivalent native
  ones.
* You should not use BasicData for anything which you need control over the
  life cycle of, e.g. ORM objects. Hypothesis will keep instances of these
  values around for a potentially arbitrarily long time and will not do any
  clean up for disposing of them other than letting them be GCed as normal.

However if it's genuinely the best way for you to do it, you should feel free to
use BasicStrategy. These caveats should be read in the light of the fact that
the full Hypothesis SearchStrategy interface is really very powerful, and the
ones using BasicStrategy are merely a bit better than the normal quickcheck
interface.


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Using the SearchStrategy API directly
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you're really super enthused about this search strategies thing and you want
to learn all the gory details of how it works under the hood, you can use the
full blown raw SearchStrategy interface to experience the full power of
Hypothesis.

This is only semi-public API, meaning that it may break between minor versions
but will not break in patch versions, but it should be considered relatively
stable and most minor versions won't break it.

.. autoclass:: SearchStrategy
  :members:
