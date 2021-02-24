RELEASE_TYPE: patch

This release lays the groundwork for automatic rewriting of simple filters,
for example converting ``integers().filter(lambda x: x > 9)`` to
``integers(min_value=10)``.

Note that this is **not supported yet**, and we will continue to recommend
writing the efficient form directly wherever possible - predicate rewriting
is provided mainly for the benefit of downstream libraries which would
otherwise have to implement it for themselves (e.g. :pypi:`pandera` and
:pypi:`icontract-hypothesis`).  See :issue:`2701` for details.
