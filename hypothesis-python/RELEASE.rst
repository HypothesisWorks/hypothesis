RELEASE_TYPE: minor

This release automatically rewrites some simple filters, such as
``integers().filter(lambda x: x > 9)`` to the more efficient
``integers(min_value=10)``, based on the AST of the predicate.

We continue to recommend using the efficient form directly wherever
possible, but this should be useful for e.g. :pypi:`pandera` "``Checks``"
where you already have a simple predicate and translating manually
is really annoying.  See :issue:`2701` for ideas about floats and
simple text strategies.
