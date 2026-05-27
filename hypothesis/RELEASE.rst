RELEASE_TYPE: patch

This patch improves shrinking - the process by which Hypothesis reduces a
failing example to a minimal one - in two ways.

First, shrinking large floats (those above ``2**53``) and collections such as
:func:`~hypothesis.strategies.lists` is now substantially faster, especially for
large inputs.

Second, we now shrink tests better when an early choice controls the size of a
later collection, such as ``n = data.draw(integers()); s =
data.draw(text(min_size=n, max_size=n))``.  Lowering ``n`` would previously
discard the (interesting) contents of ``s``, leaving the shrinker stuck on a
larger example than necessary; we now realign by truncating the recorded value.
This also helps :ref:`stateful tests <stateful>` whose rules draw such
size-dependent values (:issue:`4006`).
