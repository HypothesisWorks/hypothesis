RELEASE_TYPE: minor

This release adds a new module, ``hypothesis.extra.lark``, which you
can use to generate strings matching a context-free grammar.

In this initial version, only :pypi:`lark-parser` EBNF grammars are supported,
by the new :func:`hypothesis.extra.lark.from_lark` function.
