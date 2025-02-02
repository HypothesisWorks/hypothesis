RELEASE_TYPE: patch

Fixes a recently-introduced bug where we might have generated ``-0.0`` for ``st.floats(min_value=0.0)``, which is unsound.
