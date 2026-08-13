RELEASE_TYPE: patch

This patch fixes an internal ``AssertionError`` from
:func:`~hypothesis.strategies.from_regex` when the ``alphabet=`` argument
excludes every character which some part of the pattern could match, as in
``st.from_regex(r"\d", alphabet="abc")``.  Such patterns now raise
``InvalidArgument``, which is what we already did for literals and character
ranges outside the alphabet, and an impossible alternation branch is discarded
rather than failing the whole pattern.

Drawing from patterns which contain a character class is also somewhat faster,
because we no longer wrap each class in a redundant :func:`~hypothesis.strategies.one_of`.

Thanks to Dmitry Dygalo for this fix!
