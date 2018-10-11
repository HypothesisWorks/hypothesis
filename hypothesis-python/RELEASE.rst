RELEASE_TYPE: minor

This release substantially increases the variety of examples from the
:func:`~hypothesis.strategies.characters` strategy.

Unicode characters used to be selected by codepoint alone, which made
generation of some rare character types highly unlikely (:issue:`1401`).
Character generation now selects a Unicode category - preferring letters
to numbers to whitespace, and so on - then a code point within that category.
