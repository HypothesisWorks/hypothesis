RELEASE_TYPE: patch

This patch improves `st.register_type_strategy` when used with `namedtuple`, by preventing namedtuples from being interpreted as a sequence and provided to strategies like `st.from_type(Sequence[int])`.
