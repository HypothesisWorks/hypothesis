=================================
Innovative features of Hypothesis
=================================

This document is a guide to Hypothesis internals, mostly with a goal to porting
to other implementations of Quickcheck that want to benefit from some of the
more unusual/interesting ideas in it, but it's probably of general interest. It
assumes you have some familiarity with the general ideas of property based testing
and Quickcheck.

Nothing here is stable public API and might all be prone to change between
minor releases. The purpose of this document is to share the ideas, not to
specify the behaviour.

If you want to see all of these how most of these pieces fit together, there
is also `a worked example available here <https://github.com/DRMacIver/hypothesis/blob/master/examples/bintree.py>`_.

This is sorted roughly in order of most interesting to least technically interesting.

----------
Templating
----------

Templating is the single most important innovation in Hypothesis. If you're
going to take any ideas out of Hypothesis you should take this one.

The idea is as follows: Rather than generating data of the required type
directly, value generation is split into two parts. We first generate a *template*
and we then have a function which can reify that template, turning it into a
value of the desired type. Importantly, simplification happens on templates and
not on reified data.

This has several major advantages:

1. The templates can be of a much more restricted type than the desired output
   - you can require them to be immutable, serializable, hashable, etc without
   in any way restricting the range of data that you can generate.
2. Seamless support for mutable data: Because the mutable object you produce
   is the result of reifying the template, any mutation done by the function
   you call does not affect the underlying template.
3. Generation strategies are monads (more or less. The generation is monadic,
   the simplification rules don't strictly follow the monad laws but this isn't
   a problem in practice).

The latter is worth elaborating on: Hypothesis SearchStrategy has methods map and
flatmap, which lets you do e.g. strategy(int).map(lambda x: Decimal(x) / 100).

This gives you a new strategy for decimals, which still supports minimization.
The normal obstacle here is that you can't minimize the result because you'd
need a way to map back to the original data type, but that isn't an issue here
because you can just keep using the previous template type, minimize that, and
only convert to the new data type at the point of reification.

Making generation monadic is trickier because of the way it has to interact with
reification (you can't know what the strategy you need to draw from is until you've
reified the intermediate argument, which you can't do). The way this is solved is
pretty fiddly and involves some tricks that wouldn't work in a pure language unless
reify was also pure (and it's quite useful to allow reify to be monadic).

--------------------------
Multi-stage simplification
--------------------------

Hypothesis generally seems to try harder than classic quickcheck to produce
simple examples. Unfortunately this meant historically that simplification was
potentially *very* slow. Multi-stage simplification helps with this a lot by
avoiding large categories of behaviours that waste time.

The core idea is that there are different categories of simplification, and
once a category of simplification has stopped working you should stop trying
it even if you've changed other things. For example, if we have something like:

.. code:: python

  @given([int])
  def test_lists_are_short(xs):
    assert len(xs) < 100

then in the classic mode of quickcheck simplification, once we've found an
example which is only 100 elements long and are trying to simplify the elements
to find out if they are essential, each recursive simplification will nevertheless
try to shrink the size of the list, wasting a lot of time after each successful
shrink of an element.

The way Hypothesis solves this is to split simplification into stages: Instead
of a single function simplify, we have a list (well, generator) of simplify
functions.

This gives us the following algorithm (somewhere between python and pseudocode):

.. code:: python

  def minimize_with_shrinker(x, f, shrinker):
      """
      Greedily apply a single shrinker function to find a smaller version
      of x which satisfies f.
      """
      for s in shrinker(x):
         if f(s):
            return minimize_with_shrinker(s, f, shrinker)
      return x
   
  def shrink_pass(x, f):
     """
     Apply each shrinker in turn to minimizing an example from x
     """
     for shrinker in shrinkers:
        x = minimize_with_shrinker(x, f, shrinker)
     return x

  def minimize(x, f):
      """
      Repeatedly do minimization passes on x until we hit a fixed point
      """
      while True:
          shrunk = shrink_pass(x, f)
          if shrunk == x:
              return shrunk
          x = shrunk

So in the list example we have two simplification passes: The first attempts
to remove elements, the second attempts to simplify elements in place without
changing the size of the list.

We do multiple passes because sometimes a later pass can unblock a condition
that was making a previous pass make progress by e.g. changing relations between
elements.

In order to avoid combinatorial explosions when recursively applying simplification
one will frequently flatten down the simplification passes for elements into a
single pass, using the function


.. code:: python

  def all_shrinks(x):
      shrink in shrinkers:
          for s in shrink(x):
              yield s

Empirically this general approach seems to be much faster for classes of
example where one of the passes is constrained, while still producing high
quality results.

An additional detail: In actual fact, the function that returns the shrinkers
has access to the value to be shrunk. This is to handle the case where there
might be a very large number of potential shrinkers, most of them useless. In
the monadic case we have an infinite space of potential shrinkers because we
can only apply shrinkers from the target strategy if we know the source value.

The shrink functions returned must all be able to handle any value (in the sense of
not erroring. They don't have to do anything useful). The purpose of the argument
to shrinkers is only to immediately eliminate shrinkers that won't be useful.

---------------
Parametrization
---------------

Template generation is also less direct than you might expect. Each strategy
has two distributions: A parameter distribution, and a conditional template
distribution given a parameter value.

The idea is that a parameter value says roughly what sort of things should be
generated, and then the template distribution generates them given that
specification.

To consider a simple example, a parameter value for a generating booleans is a
number between 0 and 1 which is the probability of generating true. So in order
to draw a boolean we draw that number from a uniform distribution, then we draw
a boolean which is true with that probability.

As described, the result is indistinguishable from just flipping a coin. The
resulting bool will be true 50% of the time. The interesting thing is how
parameters compose.

Suppose we now want to draw a list of booleans. This will have a parameter value
which is a pair of numbers: The first is the expected length, the second is the
bool parameter, which is the probability of any given element being true.

This allows us to reach a lot of values that would be essentially impossible to
reach otherwise. Suppose we needed a list of length at least 20 elements all of
which are true in order to trigger a bug. Given a length of 20, if each element
is drawn independently the chances of them all being true are just under one in
a million. However with this parametrization it's one in 21 (because if you draw
a number close to 1 it makes them *all* more likely to be true). 

The idea of trying to generate this sort of "clumpier" distribution is based on
a paper called `Swarm Testing <http://www.cs.utah.edu/~regehr/papers/swarm12.pdf>`_,
but with some extensions to the idea. The essential concept is that a distribution
which is too flat is likely to spend too much time exploring uninteresting
interactions. By making any given draw focus on some particular area of the search
space we significantly increase the chances of certain interesting classes of
things happening.

The second important benefit of the parameter system is that you can use it to
guide the search space. This is useful because it allows you to use otherwise
quite hard to satisfy preconditions in your tests.

The way this works is that we store all the parameter values we've used, and
will tend to use each parameter value multiple times. Values which tend to
produce "bad" results (that is, produce a test such that assume() is called
with a falsey value and rejects the example it was given) will be chosen less
often than a parameter value which doesn't. Values which produce templates we've
already seen are also penalized in order to guide the search towards novelty.

The way this works in Hypothesis is with an infinitely many armed bandit algorithm
based on `Thompson Sampling <http://en.wikipedia.org/wiki/Thompson_sampling>`_
and some ad hoc hacks I found useful to avoid certain pathological behaviours.
I don't strongly recommend following the specific algorithm, though it seems to
work well in practice, but if you want to take a look at the code it's
`in this file <https://github.com/DRMacIver/hypothesis/blob/master/src/hypothesis/internal/examplesource.py>`_.
 
------------
The database
------------

There's not much to say here except "why isn't everyone doing this?" (though
in fairness this is made much easier by the template system).

When Hypothesis finds a minimal failing example it saves the template for it in
a database (by default a local sqlite database, though it could be anything).
When run in future, Hypothesis first checks if there are any saved examples for
the test and tries those first. If any of them fail the test, it skips straight
to the minimization stage without bothering with data generation. This is
particularly useful for tests with a low probability of failure - if Hypothesis
has a one in 1000 chance of finding an example it will probably take 5 runs of
the test suite before the test fails, but after that it will consistently fail
until you fix the bug.

The key that Hypothesis uses for this is the type signature of the test, but that
hasn't proven terribly useful. You could use the name of the test equally well
without losing much.

I had some experiments with disassembling and reassembling examples for reuse
in other tests, but in the end these didn't prove very useful and were hard to
support after some other changes to the system, so I took them out.

A minor detail that's worth bearing in mind: Because the template type of a
strategy is not considered part of its public API, it may change in a way that
makes old serialized data in the database invalid. Hypothesis handles this in a
"self-healing" way by validating the template as it comes out of the database
and silently discarding any that don't correspond to a valid template.

----------------
Example tracking
----------------

The idea of this is simply that we don't want to call a test function with the
same example twice. I think normal property based testing systems don't do this
because they just assume that properties are faster to check than it is to test
whether we've seen this one before, especially given a low duplication rate. 

Because Hypothesis is designed around the assumption that you're going to use
it on things that look more like unit tests (and also because Python is quite
slow) it's more important that we don't duplicate effort, so we track which
templates have previously been run and don't bother to reify and test them
again if they come up. As mentioned in the previous section we also then
penalize the parameter that produced them.

This is also useful for minimization: Hypothesis doesn't mind if you have
cycles in your minimize graph (e.g. if x simplifies to y and y simplifies to x)
because it can just use the example tracking system to break loops.

There's a trick to this: Examples might be quite large and we don't actually
want to keep them around in memory if we don't have to. Because of the restricted
templates, we can insist that all examples belong to a set of types that have a
stable serialization format. So rather than storing and testing the whole
examples for equality we simply serialize them and (if the serialized string is
at least 20 bytes) we take the sha1 hash of it. We then just keep these hashes
around and if we've seen the hash before we treat the example as seen.


---------------------
The strategy function
---------------------

Hypothesis uses an extensible function called strategy that basically means
"convert this object into a strategy if it's not one already". This turns out 
to be a really good API for quickcheck style things in a dynamic language,
because it means you can very often do "things that look like types" to map
to a strategy, and it also lets you do nice things like putting in custom
strategies anywhere you want.

I only mention this because I spent a lot of time with a much worse API and
it looks like this is not something that has generally been settled on very
clearly for dynamic languages. I believe the more common approach is to just
use combinators for everything, but the Hypothesis one looks a lot prettier. 
