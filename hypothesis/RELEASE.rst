RELEASE_TYPE: minor

:func:`~hypothesis.strategies.from_regex` now accepts a ``dialect=`` argument,
which selects the regular-expression dialect to emulate.  The default
``"python"`` is unchanged, while ``"jsonschema"`` follows the `subset of
ECMA-262 recommended by JSON Schema
<https://json-schema.org/understanding-json-schema/reference/regular_expressions>`__,
where ``$`` matches only at the end of the string rather than also just before
a trailing newline.  This exposes as a public API the behaviour previously used
internally by :pypi:`hypothesis-jsonschema` and :pypi:`schemathesis`
(:issue:`4089`).

Thanks to Jonnas Figueiredo for this feature!
