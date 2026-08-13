RELEASE_TYPE: patch

This patch provides a better error message for some :func:`~hypothesis.strategies.from_regex` cases where the passed pattern and alphabet were incompatible, as in ``st.from_regex(r"\d", alphabet="abc")``.

Thanks to Dmitry Dygalo for this fix!
