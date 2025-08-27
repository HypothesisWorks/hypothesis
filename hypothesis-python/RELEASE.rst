RELEASE_TYPE: patch

Fixes a race condition under threading for strategies which trigger our filter-rewriting rules, like ``st.integers().filter(lambda x: abs(x) > 100)``.
