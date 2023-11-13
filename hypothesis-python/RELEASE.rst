RELEASE_TYPE: patch

This patch adds a warning when :func:`@st.composite <hypothesis.strategies.composite>`
wraps a function annotated as returning a :class:`~hypothesis.strategies.SearchStrategy`,
since this is usually an error (:issue:`3786`).  The function should return a value,
and the decorator will convert it to a function which returns a strategy.
