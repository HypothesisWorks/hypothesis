RELEASE_TYPE: minor

The :func:`~hypothesis.strategies.from_regex` strategy now takes an optional
``alphabet=characters(codec="utf-8")`` argument for unicode strings, like
:func:`~hypothesis.strategies.text`.

This offers more and more-consistent control over the generated strings,
removing previously-hard-coded limitations.  With ``fullmatch=False`` and
``alphabet=characters()``, surrogate characters are now possible in leading
and trailing text as well as the body of the match.  Negated character classes
such as ``[^A-Z]`` or ``\S`` had a hard-coded exclusion of control characters
and surrogate characters; now they permit anything in ``alphabet=`` consistent
with the class, and control characters are permitted by default.
