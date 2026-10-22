RELEASE_TYPE: patch

This patch fixes some internal bookkeeping that could go wrong when an
exception was raised and caught during generation, for example by
|st.recursive|, which could make shrinking less effective.
