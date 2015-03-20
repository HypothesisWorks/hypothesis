====================
Hypothesis internals
====================

This document is a guide to Hypothesis internals, mostly with a goal to porting
to other implementations of Quickcheck that want to benefit from some of the
more unusual/interesting ideas in it.

Nothing here is stable public API and might all be prone to change between
minor releases. The purpose of this document is to share the ideas, not to
specify the behaviour.

This is sorted roughly in order of most interesting to least interesting.

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

1. The templates can be of a much more restricted type than the desired output - you can require them to be immutable, serializable, hashable, etc without in any way restricting the range of data that you can generate.
2. Seamless support for mutable data: Because the mutable object you produce is the result of reifying the template, any mutation done by the function you call does not affect the underlying template.
3. Generation strategies can be made functorial (and indeed applicative. You can sortof make them monadic but the resulting templates are a bit fiddly and can't really be of the desired restricted type, so it's probably not really worth it)

The latter is worth elaborating on: Hypothesis SearchStrategy has a method map
which lets you do e.g. strategy(int).map(lambda x: Decimal(x) / 100). This gives
you a new strategy for decimals, which still supports minimization. The normal
obstacle here is that you can't minimize the result because you'd need a way to
map back to the original data type, but that isn't an issue here because you
can just keep using the previous template type, minimize that, and only convert
to the new data type at the point of reification.

---------------
Parametrization
---------------

Template generation is also less direct than you might expect. Each strategy
has two distributions: A parameter distribution, and a conditional template
distribution given a parameter value.

The idea is that the parameter says roughly what sort of things should be
generated, and then the template distribution generates them given that
specification.

To consider a simple example, a parameter for a generating booleans is a single
number between 0 and 1 which is the probability of generating True. So in order
to draw a boolean we draw that number, then we draw a boolean which is true
with that probability.

As described, the result is indistinguishable from just flipping a coin. The
resulting bool will be true 50% of the time. The interesting thing is how
parameters compose.

Suppose we now want to draw a list of booleans. This will have a parameter which
is a pair of numbers: The first is the expected length, the second is the bool
parameter, which is the probability of any given element being true.

This allows us to reach a lot of values that would be essentially impossible to
reach otherwise. Suppose we needed a list of length at least 20 elements all of
which are True in order to trigger a bug. Given a length of 20, if each element
is drawn independently the chances of them all being True are just under one in
a million. However with this parametrization it's one in 21 (because if you draw
a number close to 1 it makes them *all* more likely to be True). 

The idea of trying to generate this sort of "clumpier" distributionis based on
a paper called `Swarm Testing <http://www.cs.utah.edu/~regehr/papers/swarm12.pdf>`_,
but with some extensions to the idea. The essential concept is that a distribution
which is too flat is likely to spend too much time exploring uninteresting
interactions. By making any given draw focus on some particular area of the parameter
space we significantly increase the chances of certain interesting classes of
things happening.

The second important benefit of the parameter system is that you can use it to
guide the search space. This is useful because it allows you to use otherwise
quite hard to satisfy preconditions in your tests.

The way this works is that we store all the parameters we use, and will tend to
use each parameter multiple times. Parameters which tend to produce "bad"
results (that is, produce a test such that assume() is called with a Falsey
value) will be chosen less often than a parameter which doesn't. Parameters
which produce templates we've already seen are also penalized in order to guide
the search towards novelty.

The way this works in Hypothesis is with an infinitely many armed bandit algorithm
based on Thompson Sampling and some ad hoc hacks. I don't strongly recommend
following the specific algorithm, though it seems to work well in practice.

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
