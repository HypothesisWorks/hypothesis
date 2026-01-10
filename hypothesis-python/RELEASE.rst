RELEASE_TYPE: patch

This patch fixes a bug where |st.recursive| would fail in cases where the
``extend=`` function does not reference it's argument - which was assumed
by the recent ``min_leaves=`` feature, because the strategy can't actually
recurse otherwise.  (:issue:`4638`)

Now, the historical behavior is working-but-deprecated, or an error if you
explicitly pass ``min_leaves=``.
