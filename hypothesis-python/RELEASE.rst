RELEASE_TYPE: minor

This release uses :pep:`612` :obj:`python:typing.ParamSpec` (or the
:pypi:`typing_extensions` backport) to express the first-argument-removing
behaviour of :func:`@st.composite <hypothesis.strategies.composite>`
and signature-preservation of :func:`~hypothesis.strategies.functions`
to IDEs, editor plugins, and static type checkers such as :pypi:`mypy`.
