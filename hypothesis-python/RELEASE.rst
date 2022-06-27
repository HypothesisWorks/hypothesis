RELEASE_TYPE: patch

This release automatically rewrites some simple filters, such as
``floats().filter(lambda x: x >= 10)`` to the more efficient
``floats(min_value=10)``, based on the AST of the predicate.

We continue to recommend using the efficient form directly wherever
possible, but this should be useful for e.g. :pypi:`pandera` "``Checks``"
where you already have a simple predicate and translating manually
is really annoying.  See :issue:`2701` for details.
