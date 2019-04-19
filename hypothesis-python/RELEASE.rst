RELEASE_TYPE: patch

This release refactors stateful rule selection to share the new machinery
with :func:`~hypothesis.strategies.sampled_from` instead of using the original
independent implementation.
