RELEASE_TYPE: patch

This patch fixes :issue:`2657`, where passing unicode patterns compiled with
:obj:`python:re.IGNORECASE` to :func:`~hypothesis.strategies.from_regex` could
trigger an internal error when casefolding a character creates a longer string
(e.g. ``"\u0130".lower() -> "i\u0370"``).
