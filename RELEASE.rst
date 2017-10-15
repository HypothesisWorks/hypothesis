RELEASE_TYPE: patch

This patch removes the ``mergedb`` tool, introduced in Hypothesis 1.7.1
on an experimental basis.  It has never actually worked, and the new
:doc:`Hypothesis example database <database>` is designed to make such a
tool unnecessary.
