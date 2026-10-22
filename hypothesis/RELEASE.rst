RELEASE_TYPE: patch

This patch fixes a regression in :ref:`version 6.170.1 <v6.170.1>`, where
unique collections of non-empty collections, such as
``st.sets(st.frozensets(st.integers(), min_size=1), min_size=1)``, could fail
the |HealthCheck.large_base_example| health check (:issue:`4918`).
