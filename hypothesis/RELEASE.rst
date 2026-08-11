RELEASE_TYPE: patch

This patch adds a shrinking pass for collection choices which tries lowering an
element and simplifying everything after it at the same time.  Failures which
require two elements to move together - for instance a property that only fails
while :func:`~hypothesis.strategies.binary` or :func:`~hypothesis.strategies.text`
is unsorted - will now shrink to the minimal example rather than sometimes
getting stuck part of the way there.
