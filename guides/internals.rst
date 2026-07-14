===================================
How to Work on Hypothesis Internals
===================================

This is a guide to how to work on Hypothesis internals,
with a particular focus on helping people who are new to it.
Right now it is very rudimentary and is intended primarily for people who are
looking to get started writing shrink passes as part of our `current outreach
program to get more people doing that <https://github.com/HypothesisWorks/hypothesis/issues/1093>`_,
but it will expand over time.

------------------------
Bird's Eye View Concepts
------------------------

The core engine of Hypothesis is called Conjecture.

The "fundamental idea" of Conjecture is that you can represent an arbitrary
randomized test case as the sequence of *choices* made while producing it.
Whenever the test does something "random" it instead draws the next choice from
the sequence and does what it says. Each choice is one of a small number of
typed primitives - an integer, float, boolean, string, or bytestring - and
corresponds to one of the ``draw_*`` methods on ``ConjectureData``. We call this
typed sequence the *choice sequence* (older parts of the codebase and history
may refer to it as the "IR", for intermediate representation).

These choices don't *have* to come from a PRNG, and we can run the test given
any choice sequence we like. By manipulating the choices, we can achieve more
interesting effects than pure randomness would allow us to do, while retaining
the power and ease of use of random testing. (Historically Conjecture worked
directly on the underlying byte sequence read from the PRNG; it now works on the
typed choice sequence instead, which shrinks far better because we no longer
have to reason about the encoding of each value into bytes.)

The greatest strength of this idea is that we have a single source of truth
for what an example should look like: Every choice sequence is one that *could*
have been produced by drawing from strategies, and thus is a valid thing to try
for our test. The only ways it can fail to be a valid test input are for it to
be too short or for it to not satisfy one of the test's preconditions, and both
are easily detectable.

The idea of shrinking in particular is that once we have this representation,
we can shrink arbitrary test cases based on it. We try to produce a choice
sequence that is *shortlex minimal*. What this means is that it has the shortest
possible length and among those sequences of minimal length is the smallest by
comparing choices one at a time from the left (see ``sort_key`` in
``shrinker.py``, which orders each choice by ``choice_to_index``).

Ideally we could think of the shrinker as a generic function that takes a
choice sequence satisfying some predicate and returns the shortlex minimal
sequence that also satisfies it.

We depart from this ideal in two ways:

* we can only *approximate* such a minimal sequence. Finding the actual minimum
  is intractable in general.
* we are only interested in minimizing things where the predicate goes through
  the Hypothesis API, which lets us track how the data is used and use that to
  guide the process.

We then use a number of different transformations of the choice sequence to try
and reduce our input. These vary from principled general transformations to
shameless hacks that special case something we need to work well.

One such example is the handling of floating point numbers. Floats are drawn as
a single choice, but have their own dedicated shrinker (in
``shrinking/floats.py``) which knows about our lexicographic encoding of floats
and tries shrinks - such as dropping fractional digits or moving to a nearby
integer - that only make sense for that encoding.

--------------------------
Useful Files to Know About
--------------------------

The code associated with Conjecture lives in
`src/hypothesis/internal/conjecture <https://github.com/HypothesisWorks/hypothesis/tree/master/hypothesis/src/hypothesis/internal/conjecture>`_.
There are a number of files in there,
but the most important ones are ``engine.py`` and ``data.py``.
``data.py`` defines the core type that is used to represent test cases,
and ``engine.py`` contains the main driver for deciding what test cases to run.
``shrinker.py`` contains the shrinker proper, described below.

There is also the ``shrinking/`` package, which contains a collection of
small, general purpose shrinkers for individual values - ``Integer``,
``Float``, ``String``, ``Bytes``, ``Collection``, and ``Ordering``. Each takes
a single value and a predicate over values and tries to produce a simpler value
satisfying it. Unlike the shrinker in general these don't know anything about
the testing API; the shrinker drives them with a predicate that knows how to
substitute a candidate value back into the full choice sequence and rerun the
test. This is the part of the code that means we can do things like replacing an
integer with a smaller one.

-------
Testing
-------

For general information about how to test Hypothesis, take a look at
the `testing guide <testing-hypothesis.rst>`_, but there are a couple
of areas that it's worth specifically highlighting for making changes
to the engine:

The first is `tests/conjecture/ <https://github.com/HypothesisWorks/hypothesis/tree/master/hypothesis/tests/conjecture>`_,
which is a set of unit tests designed to put the engine into particular scenarios to exercise specific behaviours,
with a goal of achieving 100% coverage on it in isolation (though it currently does not quite achieve that for some specific edge cases.
We may fix and enforce this later).

The other set of tests that are worth knowing about are the quality tests,
in `tests/quality <https://github.com/HypothesisWorks/hypothesis/tree/master/hypothesis/tests/quality>`_.
These assert specific hard to satisfy properties about the examples that Hypothesis finds -
either their existence, or something about the final shrunk result.

-----------------------
Engine Design Specifics
-----------------------

There are a couple of code patterns that are mostly peculiar to Conjecture that
you may not have encountered before and are worth being aware of.

~~~~~~~~~~~~~~~~~~~~
Search State Objects
~~~~~~~~~~~~~~~~~~~~

There are a number of cases where we find ourself with a user-provided function
(where the "user" might still be something that is entirely our code) and we
want to pass a whole bunch of different examples to it in order to achieve some
result. Currently this includes each of the main engine, the Shrinker (in
``engine.py``) and the minimizer, but there are likely to be more in future.

We typically organise such things in terms of an object that you create with
the function and possibly an initial argument that stores these on self and
has some ``run`` or similar method. They then run for a while, repeatedly
calling the function they were given.

Generally speaking they do not call the function directly, but instead wrap
calls to it. This allows them to implement a certain amount of decision caching,
e.g. avoiding trying the same shrink twice, but also gives us a place where we
can update metadata about the search process.

For objects whose goal is some form of optimisation (Shrinker, Minimizer) one
of the pieces of metadata they will typically track is a "current target". This
is typically the best example they have seen so far. By wrapping every call to
the predicate, we ensure that we never miss an example even when we're passing
through other things.

For objects whose goal is some broader form of search (currently only
``ConjectureRunner``) this also allows them to keep track of *other* examples
of interest. For example, as part of our multiple bug discovery,
``ConjectureRunner`` keeps track of the smallest example of each distinct
failure that it has seen, and updates this automatically each time the test
function is called. This means that if during shrinking we "slip" and find a
different bug than the one we started with, we will *not* shrink to that, but
it will get remembered by the runner if it was either novel or better than our
current example.

~~~~~~~~~~~
Weird Loops
~~~~~~~~~~~

The loops inside a lot of the engine look very strange and unidiomatic. For
example:

.. code-block:: python

        i = 0
        while i < len(self.shrink_target.nodes):
            if not self.consider_new_nodes(
                self.shrink_target.nodes[:i] + self.shrink_target.nodes[i + 1 :]
            ):
                i += 1

The more natural way to write this in Python would be:

.. code-block:: python

        for i in range(len(self.shrink_target.nodes)):
            self.consider_new_nodes(
                self.shrink_target.nodes[:i] + self.shrink_target.nodes[i + 1 :]
            )

This is not equivalent in this case, and would exhibit the wrong behaviour.

Every time ``consider_new_nodes`` succeeds, it changes the shape of the
current shrink target. This consequently changes the shape of the choice
sequence, both its particular values and its current length - on each loop
iteration the loop might stop either because ``i`` increases or because
``len(self.shrink_target.nodes)`` decreases.

We do not reset ``i`` to zero on success, as this would cause us to retry deleting
things that we have already tried. This *might* work, but is less likely to.
In the event that none of the earlier deletions succeed, this causes us to do
retry the entire prefix uselessly, which can result in a pass taking O(n^2) time
to do O(n) deletions.

An additional quirk is that we only increment ``i`` on failure. The reason for
this is that if we successfully deleted the choice at position ``i`` then the
node now in position ``i`` is whatever used to follow it, which is probably the
next thing we would have tried deleting if we hadn't succeeded (or something
like it), so we don't want to advance past it.
This is specific to deletion: If we are just replacing the contents of
something then we expect it to still be in the same place, so there we increment
unconditionally.
Examples of this include ``try_trivial_spans`` and ``minimize_individual_choices``.

------------
The Shrinker
------------

The shrinking part of Hypothesis is organised into a single class called ``Shrinker``
that lives in ``hypothesis/internal/conjecture/shrinker.py``.

Its job is to take an initial ``ConjectureData`` object and some predicate that
it satisfies, and to try to produce a simpler ``ConjectureData`` object that
also satisfies that predicate.

The search process mostly happens in the ``shrink`` method, which tries various
shrink passes in the ``greedy_shrink`` method and then reports on the outcome.
For details, you are strongly encouraged to read the source code.  It is very
well commented, and as the subject of active research often has newer techniques
than are documented here.

~~~~~~~~~~~~~
Search Passes
~~~~~~~~~~~~~

Search passes are methods on the ``Shrinker`` class. They are
designed to take the current shrink target and try a number of things that might
be sensible shrinks of it.

Typically the design of a search pass is that it should always try to run to
completion rather than exiting as soon as it's found something good, but that
it shouldn't retry things that are too like stuff it has already tried just
because something worked. So for example in the above loop, we try deleting
each interval (these roughly correspond to regions of the input that are
responsible for some particular value or small number of adjacent values).
When we succeed, we keep going and try deleting more intervals, but we don't
try to delete any intervals before the current index.

The reason for this is that retrying things from the beginning might work but
probably won't. Thus if we restarted every time we made a change we would end
up doing a lot of useless work. Additionally, they are *more* likely to work
after other shrink passes have run because frequently other changes are likely
to unlock changes in the current pass that were previously impossible. e.g.
when we reorder some examples we might make a big region deletable that
previously contained something critical to the relevant behaviour of the test
but is now just noise.

Because the shrinker runs in a big loop, if we've made progress the shrink pass
will always be run again (assuming we don't hit some limit that terminates the
shrink early, but by making the shrinker better we try to ensure that that
never happens).
This means that we will always get an opportunity to start again later if we
made progress, and if we didn't make progress we've tried everything anyway.


~~~~~~~~~~~~~~~~~~~~~~~
Expensive Shrink Passes
~~~~~~~~~~~~~~~~~~~~~~~

We have a bunch of search passes that are considered "expensive". Typically
this means "quadratic or worse complexity". When shrinking we initially don't
run these, and the first time that we get to the end of our main passes and
have failed to make the input any smaller, we then turn them on.

This allows the shrinker to switch from a good but slightly timid mode while its
input is large into a more aggressive DELETE ALL THE THINGS mode once that stops
working. By that point we've usually made our input small enough that quadratic
complexity is acceptable.

We turn these on once and then they stay on. The reason for this is to avoid a
"flip-flopping" scenario where an expensive pass unlocks one trivial change that
the cheap passes can find and then they get stuck again and have to do an extra
useless run through the passes to prove that.

~~~~~~~~~~~~~~~~~~~~~~
Adaptive Shrink Passes
~~~~~~~~~~~~~~~~~~~~~~

A useful trick that some of the shrink passes use is to try a thing and if it
doesn't work take a look at what the test function did to guess *why* it didn't
work and try to repair that.

The main example is ``try_shrinking_nodes``, which is used by the passes that
minimize individual choices. When it lowers one or more choices and the result
doesn't satisfy the predicate, it inspects what the test function did:

* If the attempt was *misaligned* - the test tried to draw a choice of a
  different type or size than the one we substituted, which commonly happens
  when an earlier choice controls the size of a later collection - it tries to
  realign the tree, for example by truncating a string to the size the test
  actually asked for.
* Otherwise, if the attempt lost some nodes (e.g. lowering a value made a
  following list shorter), it tries deleting the corresponding region of the
  choice sequence immediately after the lowered choice to see if that repairs
  the shape.


--------------
Playing Around
--------------

I often find that it is informative to watch the shrink process in action using
Hypothesis's verbosity settings. This can give you an idea of what the format
of your data is, and how the shrink process transforms it.

In particular, it is often useful to run a test with the flag ``-s`` to tell it
not to hide output and the environment variable ``HYPOTHESIS_VERBOSITY_LEVEL=debug``.
This will give you a very detailed log of what the testing process is running,
along with information about what passes in the shrinker are running and how
they transform it.

---------------
Getting Started
---------------

The best way of getting started on working on the engine is to work on the
shrinker. This is because it has the most well defined problems, the best
documented code among the engine, and it's generally fun to work on.

If you have not already done so, check out `Issue #1093 <https://github.com/HypothesisWorks/hypothesis/issues/1093>`_,
which collates a number of other issues about shrink quality that are good starting
points for people.

The best place to get started thus is to take a look at those linked issues and
jump in and try things! Find one that you think sounds fun. Note that some
of them suggest not doing these as your first foray into the shrinker, as some
are harder than others.

*Please* ask questions if you have any - either the main issue for general
purpose questions or specific issues for questions about a particular problem -
if you get stuck or if anything doesn't make sense. We're trying to make this
process easier for everyone to work on, so asking us questions is actively
helpful to us and we will be very grateful to you for doing so.
