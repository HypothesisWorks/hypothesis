RELEASE_TYPE: patch

The ``--hypothesis-show-statistics`` report now accounts for the
|Phase.explain| phase separately, rather than including its runtime and test
cases in the |Phase.shrink| phase (:issue:`4179`).
