RELEASE_TYPE: patch

This release fixes some extremely specific circumstances that probably have
never occurred in the wild where users of
:func:`~hypothesis.searchstrategy.deferred` might have seen a RuntimeError from
too much recursion, usually in cases where no valid example could have been
generated anyway.
