RELEASE_TYPE: patch

This patch fixes several :func:`~hypothesis.strategies.from_regex` bugs
(:issue:`4857`, :issue:`4858`, and :issue:`4859`):

* Character classes which combine a negative category with other members, like
  ``[\W_]``, now match the union of their members instead of incorrectly
  excluding characters.
* Patterns compiled with the :obj:`python:re.ASCII` flag are now handled
  correctly: inverted categories such as ``\D`` match the complement of their
  ascii counterpart, including non-ascii characters; explicit characters and
  ranges in character classes are not restricted to ascii; and only ascii
  characters casefold under :obj:`python:re.IGNORECASE`.
* Subpatterns which cannot be generated from the ``alphabet``, but may be
  repeated zero times - like ``b*`` in ``st.from_regex(r"a*b*", alphabet="a")``
  - no longer raise an error.
