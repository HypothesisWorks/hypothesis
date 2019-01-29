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
3. Implementation tricks used in our internals, for interestd contributors

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

In a worst-case scenario, the performance of filtering could be arbitarily
bad, while a 'generate and scale' approach would mean that simple inputs
could lead to irrational outputs.  Instead, we choose an imaginary part
between +/- max_magnitute, then calculate the resulting bounds on the real
part and draw it from a strategy that will always be valid.  This ensures
that the imaginary part shrinks to zero first, as we think real-valued
complex numbers are simpler than imaginary-valued complex numbers.


Keep things local
~~~~~~~~~~~~~~~~~
Hypothesis' shrinking engine sees every example as a labelled tree of choices,
with possible reductions represented as operations on the tree.  An attempted
shrink succeeds if the new tree can be converted into an example, and the
resulting example triggers the same bug in the test function.

The simplest way to keep things local is to ensure that any ``.filter(...)``
or ``assume(...)`` calls you use are as close as possible to the relevant part
of the strategy.  That way, Hypothesis can retry just the part that failed
instead of the entire strategy, which might be much slower.

For efficient shrinking, local operations on the tree should correspond with
valid (and preferably local) shrinks to the final example.  For example:

.. code:: python

    # This form of loop is hard to shrink, because we'd have to reduce
    # iterations and delete anything in the loop simultaneously.
    # We *do* try this, but it's relatively expensive.
    iterations = draw(integers(0, 10))
    for _ in range(iterations):
        ...
        draw(...)
        ...

    # In this form, the shrinker can see a repeated struture of labels and
    # delete one loop iteration without touching anything else.  Much better!
    while draw(integers(0, x)) > threshold:
        ...
        draw(...)
        ...

Similarly, it's better to draw all the attributes or inputs you need for an
object at the same time, again so they can be modified or deleted together.

The exact behaviour of the shrinking is a topic of active research and
development, so if you are interested in the details we recommend reading
the "internals.rst" guide and the well-commented source code in
``hypothesis.internal.conjecture``.  An earlier (mid-2018) version is
illustrated in David's draft paper *Test-Case Reduction for Free*,
along with an extensive evaluation.  Contact him if you would like a copy.


-------------------------------------
Shrinking in the Hypothesis internals
-------------------------------------

Note: these tricks rely on implementation details that are not available
to third-party libraries or users, but which are occasionally indispensible
to get good performance in underlying primitives.
This last section is therefore written for Hypothesis contributors.


"Shrink Open"
~~~~~~~~~~~~~
Where filtering would impose an unacceptable performance cost - usually
worst-case performance with adversarial constraints on the strategy - we
need a better trick. Fortunately we have one which works *at a low level*;
we use it in several crucial places internally but it may not be of any use
for external strategies.

Aside from anything else, **this uses private internals which may be broken
in any patch release**.  If you intend to try this, please contact us for
advice first and we may be able to provide a more robust way to do it.

Basically, we ensure that the example we draw has a simple representation
in the buffer that we can shrink from, even if that's not how we really
generated it.

First, the "one-shot filter":

- Try to draw an example from ``Maybe``, a strategy that might or might
  not give us a valid example on the first attempt.  If this succeeds,
  we're done.
- If it fails, use an internal API to mark it as invalid.  Then, create
  a more expensive or less consistent (see below) strategy that will
  generate an example which *could have come from* ``Maybe`` and draw
  that example.  Mark this invalid too.  Finally, calculate the buffer
  that would generate this example from ``Maybe``, and use another internal
  API to append it to the buffer.

When we go to shrink such a buffer, there are two possibilities:  either
the first attempt to draw from ``Maybe`` worked, and it shrinks the easy
way.  Otherwise, we delete the two draws that were marked invalid, and
try to draw an example from ``Maybe`` using the bytes we wrote - and if
we got this right, that works and gives the same example we got during
the generation phase!

(you might be able to guess we use this technique as little as possible)

The second variant lets us use a simple strategy in the shrinking phase,
but generate (most of) our new examples from a more complex strategy with
a different distribution.  For example:

1. Draw a byte, a unicode category, and a character from that category.
2. If the byte is nonzero, write the index of that character to the buffer.
   Otherwise, draw an index and use the character at that index instead.

This experimental approach generates exotic `unicode characters
<https://github.com/Zac-HD/hypothesis/blob/f1f951d67f9161947a298db8d5aa12b24a633c2b/hypothesis-python/src/hypothesis/searchstrategy/strings.py#L78-L97>`_
much more often than uniform generation, but preserves our codepoint-based
shrinking order.  `See here for more <https://github.com/HypothesisWorks/hypothesis/issues/1401>`_.


Consistent representation of repeated choices
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
This comes up when choosing which action to take in stateful testing, where
we would like deleting any single step to still give us a valid buffer (though
perhaps one which doesn't reproduce the bug).

That means that we need to choose from the same list of options every time,
even though some might be ruled out by preconditions.  We now implement this
mainly via the 'shrink open' trick (it's very versatile), but have used other
approaches in the past.

When choosing a possible value for a "bundle" in stateful testing
(analogous to a stask of variables), we use an index from the *end* and can
therefore remove more distant early entries without disturbing the relevant
part of the test case.  Search hypothesis/stateful.py for "shrink" and you'll
find the explanatory comments.
