RELEASE_TYPE: patch

:func:`~hypothesis.strategies.from_regex` no longer raises ``AttributeError``
for a bytes pattern containing a negated single character, such as
``rb"[^a]"``, compiled with ``re.IGNORECASE``.
