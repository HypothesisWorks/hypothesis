RELEASE_TYPE: patch

This patch fixes several :func:`~hypothesis.strategies.from_regex` bugs
(:issue:`4857`, :issue:`4858`, and :issue:`4859`):

* Character classes which combine a negative category with other members, like
  ``[\W_]``, now match the union of their members instead of incorrectly
  excluding characters.
* The :obj:`python:re.ASCII` flag no longer restricts inverted categories such
  as ``\D`` (which matches all non-ascii characters), explicit characters or
  ranges in character classes, or casefolding of non-ascii characters.
* Subpatterns which cannot be generated from the ``alphabet``, but may be
  repeated zero times - like ``b*`` in ``st.from_regex(r"a*b*", alphabet="a")``
  - no longer raise an error.
