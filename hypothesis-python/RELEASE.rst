RELEASE_TYPE: patch

Speed up usages of |st.sampled_from| by deferring evaluation of its repr, and truncating its repr for large collections (over 512 elements). This is especially noticeable when using |st.sampled_from| with large collections. The repr of |st.sampled_from| strategies involving sequence classes with custom reprs may change as a result of this release.
