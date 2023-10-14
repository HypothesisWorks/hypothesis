RELEASE_TYPE: patch

This patch improves `st.register_type_strategy` when used with `tuple` subclasses, by preventing them from being interpreted as generic and provided to strategies like `st.from_type(Sequence[int])`.
