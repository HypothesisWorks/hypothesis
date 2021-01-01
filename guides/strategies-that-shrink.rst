===================================
Designing strategies to shrink well
===================================

Reducing test cases to a minimal example is a great feature of Hypothesis,
the implementation of which depends on both the shrinking engine and the
structure of the strategy (or combination of strategies) which created the
example to reduce.

This document is organised into three parts:

1. How to tell if you need to think about shrinking (you probably don't!)
2. Designing for shrinking 'above' the Hypothesis public API
3. Implementation tricks used in our internals, for interested contributors

It is written for people implementing complex third-party strategies (such
as `hypothesis-networkx <https://pypi.org/project/hypothesis-networkx/>`__),
current or potential contributors to Hypothesis itself, and anyone interested
in how this works under the hood.


------------------------------------
Do you need to design for shrinking?
------------------------------------
You should only attempt to tune custom strategies for better shrinking
behaviour if more time would otherwise be spent reducing examples by hand
or debugging more complex examples.  It *may* be worthwhile if:

- Your custom strategy will be used by many people, so that spending
  the same effort tuning the strategy has much larger benefits, or
- You have personally spent time debugging failures which better example
  shrinking could have avoided and think this might happen again.

If neither of these apply to you, relax!  Hypothesis' test-case reduction
is among the best in the world, and our built-in strategies are carefully
designed to work well with it as discussed below.


------------------------------------
Shrinking for third-party strategies
------------------------------------

That is, strategies built out of other strategies until you get down to
Hypothesis' public API.  These often but not always use ``@composite``.


Composition of shrinking
~~~~~~~~~~~~~~~~~~~~~~~~
The first and most important rule is that Hypothesis shrinks from the
'bottom up'.  If any component of your strategy is replaced with a simpler
example, the end result should also become simpler.  We usually try to define
"simpler" here to match a reasonable intuition about the strategy, and avoid
weird edge cases when it's combined with another strategy or predicate.

`Issue #1076 <https://github.com/HypothesisWorks/hypothesis/issues/1076>`_,
where magnitude constraints were added to the ``complex_numbers`` strategy,
makes a nice case study.  We wanted to continue shrinking the real and
imaginary parts like ``builds(complex, floats(), floats())``.

In a worst-case scenario, the performance of filtering could be arbitrarily
bad, while a 'generate and scale' approach would mean that simple inputs
could lead to irrational outputs.  Instead, we choose an imaginary part
between +/- max_magnitude, then calculate the resulting bounds on the real
part and draw it from a strategy that will always be valid.  This ensures
that the imaginary part shrinks to zero first, as we think real-valued
complex numbers are simpler than imaginary-valued complex numbers.


Let generation be lucky
~~~~~~~~~~~~~~~~~~~~~~~
Sometimes, it's worth searching for a particularly nasty value to try.
This trick should be used sparingly, and always behind a branch that the
shrinker can decide not to take such as ``if draw(booleans()):``, but might
occasionally worth trying.  Measure the results before you keep it!

`Issue #69 <https://github.com/HypothesisWorks/hypothesis/issues/69>`_ provides
a nice case study: when generating tz-aware datetimes, we would like to generate
instants that are skipped or repeated due to a daylight-savings transition more
often than by chance.  Of course, there may or may not be any such moments
allowed by the bounds and tz strategy!

Eliding much of the detail, a key part is to find such a moment between two
endpoints, when we can only check whether one or more exists.  The traditional
approach would be to use a binary search, but this would be relatively expensive
to shrink as we would pay the log-n cost on every attempted shrink.

Instead of choosing the midpoint, we draw a *random* point between our known
endpoints, and repeat this until we find a satisfactory moment.  This allows
the shrinker to delete all the intermediate draws - and appear lucky enough
to find the moment we were looking for on the first guess!


Keep things local
~~~~~~~~~~~~~~~~~
Hypothesis' shrinking engine sees every example as a labelled tree of choices,
with possible reductions represented as operations on the tree.  An attempted
shrink succeeds if the new tree can be converted into an example, and the
resulting example triggers the same bug in the test function.

The most common way we see users breaking data locality is by drawing a size,
then drawing a collection of that size.  This is tempting because it's simple
and it _works_, but it's often much slower than the alternatives.

.. code:: python

    # Both of these strategies can generate exactly the same kind of examples,
    # but the second has better performance as well as style.
    integers(0, 10).flatmap(lambda n: st.lists(..., min_size=n, max_size=n))
    st.lists(..., min_size=1, max_size=10)

Another easy way to keep things local is to ensure that any ``.filter(...)``
or ``assume(...)`` calls you use are as close as possible to the relevant part
of the strategy.  That way, Hypothesis can retry just the part that failed
instead of the entire strategy, which might be much slower.

For efficient shrinking, local operations on the tree should correspond with
valid (and preferably local) shrinks to the final example.  For example:

.. code:: python

    # This form of loop is hard to shrink, because we'd have to reduce `n` and
    # delete something in the loop simultaneously.  It's equivalent to the
    # `.flatmap` example above.  We _do_ shrink this, but much more slowly.
    n = draw(integers(0, 10))
    for _ in range(n):
        ...
        draw(...)
        ...

    # In this form, the shrinker can see a repeated structure of labels
    # and delete one loop iteration without touching anything else.
    # We use a variant of this trick to generate collections internally!
    while draw(integers(0, x)) > threshold:
        ...
        draw(...)
        ...

Similarly, it's better to draw all the attributes or inputs you need for an
object at the same time, again so they can be modified or deleted together.

The exact behaviour of the shrinking is a topic of active research and
development, so if you are interested in the details we recommend reading
the `internals guide <https://github.com/HypothesisWorks/hypothesis/blob/master/guides/internals.rst>`_
and the well-commented source code in
``hypothesis.internal.conjecture`` as well as David's ECOOP 2020 paper
`Test-Case Reduction via Test-Case Generation: Insights From the Hypothesis Reducer
<https://2020.ecoop.org/details/ecoop-2020-papers/13/Test-Case-Reduction-via-Test-Case-Generation-Insights-From-the-Hypothesis-Reducer>`__.


-------------------------------------
Shrinking in the Hypothesis internals
-------------------------------------
The last section is for current or prospective Hypothesis contributors only.

These tricks rely on implementation details that are not available to
third-party libraries or users, **and can change in any patch release**.
Occasionally they are also indispensable to get good performance in underlying
primitives, so please contact us if the public API is not enough and we may
be able to work something out.


What do internals get you?
~~~~~~~~~~~~~~~~~~~~~~~~~~
Using the low-level, internal APIs complements, rather than changing, the
principles above.  The bytestream-level view has some important advantages:

Because we operate at the level of bits, the relationship between a value and
the corresponding buffer is much more obvious.  If we're careful, that means
we can calculate the value we want and then write the corresponding buffer
to recreate it when the test case is shrunk or replayed.

A small step up from bits, we can also see the spans that indicate a subset
of the buffer to consider for various transformations such as transposition
or deletion.

Sometimes these features are the only way to maintain acceptable performance
in very rare or even pathological cases - consider shrinking a complex number
with a single allowed magnitude - but it's almost certain that someone will
need the core strategies to do just that.
However, using low-level APIs also comes at a cost - they are verbose and
generally more difficult to use, and can violate key invariants of the engine
if misused.

Internally, our strategies mostly use the public API or something that looks
a lot like ``@composite``, so it's fairly easy to follow along.  There are
just a few tricks enabled by those low-level advantages that we wanted to
name and document, so we can recognise them discuss them and invent more...


Make your own luck
~~~~~~~~~~~~~~~~~~
This is the simplest trick that uses our ability to write choices to the
buffer.  We use it for ``sampled_from(...).filter(...)``, after trying an
initial draw with the usual rejection sampling technique, and added the
``SearchStrategy.do_filtered_draw`` method so other strategies can opt-in
as we design similar tricks for their structure.

It was originally designed for stateful testing, where "lucky generation"
might be inefficient if there are many rules but only a few allowed by their
preconditions.  Here's how it works for stateful testing:

1. Draw an index into the unfiltered list of rules.  Return the corresponding
   rule if it's allowed - we got lucky!  (or someone set us up...)
2. Create a list of allowed rules, and choose one from that shortlist instead.
3. Find the index of the chosen rule *in the unfiltered list*, and write that
   index to the buffer.  Finally, return the chosen rule.

When the shrinker tries to delete the first two draws, the resulting buffer
will lead to the same rule being chosen at step *one* instead.  We've made
our own luck!

This trick is especially useful when we want to avoid rejection sampling
(the ``.filter`` method, ``assume``) for performance reasons, but also
need to give the shrinker the same low-level representation for each instance
of a repeated choice.


Flags "shrink open"
~~~~~~~~~~~~~~~~~~~
An important insight from `Swarm Testing (PDF) <https://www.cs.utah.edu/~regehr/papers/swarm12.pdf>`__
is that randomly disabling some features can actually reduce the expected time
before finding a bug, because some bugs may be suppressed by otherwise common
features or attributes of the data.

As discussed on  `issue #1401 <https://github.com/HypothesisWorks/hypothesis/issues/1401>`__,
there are a few points to keep in mind when implementing shrinkable swarm testing:

- You need swarm flags to "shrink open" so that once the shrinker has run to
  completion, all flags are enabled. e.g. you could do this by generating a
  set of banned flags.
- You need to use rejection sampling rather than anything more clever, or at
  least look like it to the shrinker.  (see e.g. *Make your own luck*, above)

Taking Unicode as an example, we'd like to use our knowledge of Unicode
categories to generate more complex examples, but shrink the generated string
without reference to categories.  While we haven't actually implemented this
yet - it's pretty hairy - the simple version of the idea goes like this:

1. Generate a set of banned categories.
2. Use ``characters().filter(category_is_not_banned)``

When shrinking, we start by removing categories from the banned set, after
which characters in the string can be reduced as usual.  In a serious version,
the make-your-own-luck approach would be essential to make the filter
reasonably efficient, but that's not a problem internally.

In more complicated structures, it would be nice to generate the flags on first
use rather than up front before we know if we need them.  The trick there is
to write each flag to the buffer every time we check it, in such a way that if
we delete the first use the second turns into an initialisation.


Explicit example boundaries
~~~~~~~~~~~~~~~~~~~~~~~~~~~
This is almost always handled implicitly, e.g. by ``cu.many``, but *sometimes*
it can be useful to explicitly insert boundaries around draws that should be
deleted simultaneously using ``data.start_example``.  This is used to group
the value and sign of floating-point numbers, for example, which we split up
in order to provide a more natural shrinking order.

Explicit example management can also be useful to delineate variably-sized
draws, such as our internal helper ``cu.biased_coin``, which makes eliminating
dead bytes much cheaper.  Finally, labelling otherwise indistinguishable draws
means the shrinker can attempt to swap only the like values.
