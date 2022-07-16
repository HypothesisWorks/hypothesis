RELEASE_TYPE: patch

Issue a deprecation warning if a function decorated with `st.composite` does not reference its first argument (which is typically `draw`).

A couple of tests triggered this warning, so we also fix those tests.
