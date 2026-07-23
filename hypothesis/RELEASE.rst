RELEASE_TYPE: patch

:func:`~hypothesis.extra.lark.from_lark` could generate strings which the
grammar's lexer tokenizes differently than the terminal they were generated
for, and which therefore fail to parse - for example ``'"""'`` for Lark's
built-in ``ESCAPED_STRING`` terminal (:issue:`4325`). Terminal strategies now
only generate strings which the lexer would match in their entirety.
