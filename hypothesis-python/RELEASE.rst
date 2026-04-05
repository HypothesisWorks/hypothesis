RELEASE_TYPE: patch

This patch improves printing of primitive values generated from complex
strategies, particularly for :func:`~hypothesis.strategies.from_regex`.
Previously, these would often be printed as function calls desctribing
how to construct them. Now they will always be printed as a literal value.
