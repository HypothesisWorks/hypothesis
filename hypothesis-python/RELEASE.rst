RELEASE_TYPE: minor

The ``alphabet=`` argument to :func:`~hypothesis.strategies.from_regex`
now accepts unions of :func:`~hypothesis.strategies.characters` and
:func:`~hypothesis.strategies.sampled_from` strategies, in addition to
accepting each individually.

This patch also fixes a bug where ``text(...).filter(re.compile(...).match)``
could generate non-matching instances if the regex pattern contained ``|``
(:issue:`4008`).
