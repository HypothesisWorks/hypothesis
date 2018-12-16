RELEASE_TYPE: patch

This patch refactors the ``hypothesis.strategies`` module, so that private
names should no longer appear in tab-completion lists.  We previously relied
on ``__all__`` for this, but not all editors respect it.
