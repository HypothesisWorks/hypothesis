RELEASE_TYPE: patch

This patch fixes the internals for :func:`~hypothesis.strategies.integers`
with one bound.  Values from this strategy now always shrink towards zero
instead of towards the bound, and should shrink much more efficiently too.
On Python 2, providing a bound incorrectly excluded ``long`` integers,
which can now be generated.
