RELEASE_TYPE: patch

This patch improves the performance of |st.one_of| when it can be simplified to a single real strategy, for example ``st.integers() | st.nothing()``.
