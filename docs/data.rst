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


.. code:: python

    >>>> from hypothesis import strategy
    >>>> from hypothesis.specifiers import streaming
    >>>> x = strategy(streaming(int)).example()
    >>>> x
    Stream(...)
    >>>> x[2]
    209
    >>>> x
    Stream(32, 132, 209, ...)
    >>>> x[10]
    130
    >>>> x
    Stream(32, 132, 209, 843, -19, 58, 141, -1046, 37, 243, 130, ...)

Think of a Stream as an infinite list where we've only evaluated as much as
we need to. As per above, you can index into it and the stream will be evaluated up to
that index and no further.

You can iterate over it too (warning: iter on a stream given to you
by Hypothesis in this way will never terminate):

.. code:: python

    >>>> it = iter(x)
    >>>> next(it)
    32
    >>>> next(it)
    132
    >>>> next(it)
    209
    >>>> next(it)
    843

Slicing will also work, and will give you back Streams. If you set an upper
bound then iter on those streams *will* terminate:

.. code:: python

    >>>> list(x[:5])
    [32, 132, 209, 843, -19]
    >>>> y = x[1::2]
    >>>> y
    Stream(...)
    >>>> y[0]
    132
    >>>> y[1]
    843
    >>>> y
    Stream(132, 843, ...)

You can also apply a function to transform a stream:

.. code:: python

    >>>> t = strategy(streaming(int)).example()
    >>>> tm = t.map(lambda n: n * 2)
    >>>> tm[0]
    26
    >>>> t[0]
    13
    >>>> tm
    Stream(26, ...)
    >>>> t
    Stream(13, ...)

map creates a new stream where each element of the stream is the function
applied to the corresponding element of the original stream. Evaluating the
new stream will force evaluating the original stream up to that index.

(Warning: This isn't the map builtin. In Python 3 the builtin map should do
more or less the right thing, but in Python 2 it will never terminate and
will just eat up all your memory as it tries to build an infinitely long list)

These are the only operations a Stream supports. There are a few more internal
ones, but you shouldn't rely on them.

-------------------
Adapting strategies
-------------------

Often it is the case that a strategy doesn't produce exactly what you want it
to and you need to adapt it. Sometimes you can do this in the test, but this
hurts reuse because you then have to repeat the adaption in every test.

Hypothesis gives you ways to build strategies from other strategies given
functions for transforming the data.

~~~~~~~
Mapping
~~~~~~~

Map is probably the easiest and most useful of these to use. If you have a
strategy s and a function f, then an example s.map(f).example() is
f(s.example()). i.e. we draw an example from s and then apply f to it.

e.g.:

.. code:: python

  >>> strategy([int]).map(sorted).example()
  [1, 5, 17, 21, 24, 30, 45, 82, 88, 88, 90, 96, 105]

Note that many things that you might use mapping for can also be done with the
builds function in hypothesis.strategies.

~~~~~~~~~
Filtering
~~~~~~~~~

filter lets you reject some examples. s.filter(f).example() is some example
of s such that f(s) is truthy.

.. code:: python

  >>> strategy(int).filter(lambda x: x > 11).example()
  1873
  >>> strategy(int).filter(lambda x: x > 11).example()
  73

It's important to note that filter isn't magic and if your condition is too
hard to satisfy then this can fail:

.. code:: python

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


.. code:: python

  >>> strategy((int, int)).map(
  ... lambda x: tuple(sorted(x))).filter(lambda x: x[0] != x[1]).example()
  (42, 1281698)

~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Chaining strategies together
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Finally there is flatmap. Flatmap draws an example, then turns that example
into a strategy, then draws an example from *that* strategy.

It may not be obvious why you want this at first, but it turns out to be
quite useful because it lets you generate different types of data with
relationships to eachother.

For example suppose we wanted to generate a list of tuples all of the same
length:

  >>> strategy(
  ... integers_in_range(0, 10)).flatmap(lambda n: [(int,) * n]).example()
  [(170, -747, 564), (-534, 7226, 4), (83, 11647, 170)]

In this example we first choose a length for our tuples, then we build a
description of a list of tuples of those lengths.

Most of the time you probably don't want flatmap, but unlike filter and map
which are just conveniences for things you could just do in your tests,
flatmap allows genuinely new data generation that you wouldn't otherwise be
able to easily do.

(If you know Haskell: Yes, this is more or less a monadic bind. If you don't
know Haskell, ignore everything in these parentheses. You do not need to
understand anything about monads to use this, or anything else in Hypothesis).

--------------------------------
Defining entirely new strategies
--------------------------------

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


-------------------------------------
Using the SearchStrategy API directly
-------------------------------------

If you're really super enthused about this search strategies thing and you want
to learn all the gory details of how it works under the hood, you can use the
full blown raw SearchStrategy interface to experience the full power of
Hypothesis.

This is only semi-public API, meaning that it may break between minor versions
but will not break in patch versions, but it should be considered relatively
stable and most minor versions won't break it.

.. autoclass:: SearchStrategy
  :members: produce_parameter, produce_template, reify, simplifiers, basic_simplify,
    full_simplify, to_basic, from_basic 
