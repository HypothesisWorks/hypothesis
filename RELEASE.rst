RELEASE_TYPE: patch

:func:`~hypothesis.strategies.from_type` can now resolve recursive types
such as binary trees (:issue:`1004`).  Detection of non-type arguments has
also improved, leading to better error messages in many cases involving
:pep:`forward references <484#forward-references>`.
