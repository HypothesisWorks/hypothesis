RELEASE_TYPE: patch

This patch fixes a bug where integer choice constraints with probability weights
failed to distinguish between different weight distributions over identical keys
in ``choice_constraints_key`` (:issue:`4908`).
