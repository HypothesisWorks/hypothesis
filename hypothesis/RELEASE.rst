RELEASE_TYPE: minor

|st.from_regex| now takes a ``dialect=`` argument, which selects the flavour of
regex semantics used to generate strings: ``"python"`` (the default) is
unchanged, while ``"jsonschema"`` follows the `ECMA-262 subset recommended by
JSON Schema <https://json-schema.org/understanding-json-schema/reference/regular_expressions>`__,
where ``$`` matches only at the end of the string instead of also matching just
before a trailing newline (:issue:`4089`).

Thanks to Su Ru for this feature!
