RELEASE_TYPE: patch

This release improves the internal representation of integers. This should have relatively
little user visible difference, but will improve performance of both generation and shrinking
in some cases, and also will improve shrink quality in a few others. In particular code like
``st.one_of(st.integers(), st.text())`` should now reliably prefer ``0`` over ``""``.
