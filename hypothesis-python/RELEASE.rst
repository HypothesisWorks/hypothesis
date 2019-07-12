RELEASE_TYPE: patch

This patch improves the behaviour of the :func:`~hypothesis.strategies.text`
strategy when passed an ``alphabet`` which is not a strategy.  The value is
now interpreted as ``whitelist_characters`` to :func:`~hypothesis.strategies.characters`
instead of a sequence for :func:`~hypothesis.strategies.sampled_from`, which
standardises the distribution of examples and the shrinking behaviour.

You can get the previous behaviour by using
``lists(sampled_from(alphabet)).map("".map)`` instead.
