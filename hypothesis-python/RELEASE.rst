RELEASE_TYPE: patch

This patch makes :func:`~hypothesis.stateful.multiple` iterable, so that
output like ``a, b = state.some_rule()`` is actually executable and
can be used to reproduce failing examples.

Thanks to Vincent Michel for reporting and fixing :issue:`2311`!
